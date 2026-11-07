using System.Diagnostics;
using Microsoft.Xna.Framework.Audio;
using StardewModdingAPI;
using StardewValley;
using StardewValley.TokenizableStrings;

namespace StardewZoo;

internal sealed class RecordingManager
{
    private const int PollTicks = 60;
    private static readonly TimeSpan ToolTimeout = TimeSpan.FromSeconds(12);
    private static readonly TimeSpan MicGrace = TimeSpan.FromSeconds(2.5);

    private readonly IModHelper helper;
    private readonly IMonitor monitor;
    private readonly Dictionary<string, (DateTime Time, long Size)> stamps = new(StringComparer.OrdinalIgnoreCase);
    private readonly Dictionary<string, bool> custom = new(StringComparer.OrdinalIgnoreCase);
    private ZooSaveData save = new();
    private int ticks;

    private string? jobAnimal;
    private string? jobTemp;
    private Task<ToolOutcome>? toolJob;
    private Microphone? microphone;
    private readonly List<byte> capture = new();
    private int captureNeeded;
    private DateTime micDeadline;

    private sealed record ToolOutcome(string? Via, bool Silent, string Detail);

    public RecordingManager(IModHelper helper, IMonitor monitor)
    {
        this.helper = helper;
        this.monitor = monitor;
    }

    public string SoundsDir => Path.Combine(this.helper.DirectoryPath, "sounds");

    public string DefaultsDir => Path.Combine(this.SoundsDir, "defaults");

    public bool Busy => this.jobAnimal != null;

    public string? BusyAnimal => this.jobAnimal;

    /// <summary>Latest result to show in the studio menu.</summary>
    public string Status { get; private set; } = "";

    public void Initialize(ZooSaveData save)
    {
        this.save = save;
        this.stamps.Clear();
        this.custom.Clear();
        Directory.CreateDirectory(this.SoundsDir);
        foreach (string animal in ZooIds.AnimalTypes)
        {
            string name = ZooIds.ShortName(animal);
            string live = this.WavPath(name);
            string baked = this.DefaultPath(name);
            if (!File.Exists(live) && File.Exists(baked))
                File.Copy(baked, live, overwrite: false);
            this.Reload(name, announce: false);
        }
        this.Status = "";
    }

    public void Tick()
    {
        if (this.microphone != null)
            this.TickMicrophone();
        else if (this.toolJob is { IsCompleted: true })
            this.FinishToolJob();

        if (++this.ticks % PollTicks == 0 && !this.Busy)
            this.PollChanges();
    }

    public string WavPath(string shortName) => Path.Combine(this.SoundsDir, shortName + ".wav");

    public string DefaultPath(string shortName) => Path.Combine(this.DefaultsDir, shortName + ".wav");

    public bool IsCustom(string shortName) => this.custom.TryGetValue(shortName, out bool value) && value;

    public string DisplayName(string shortName)
    {
        if (Game1.farmAnimalData != null && Game1.farmAnimalData.TryGetValue("StardewZoo." + shortName, out var data) && !string.IsNullOrWhiteSpace(data.DisplayName))
            return TokenParser.ParseText(data.DisplayName);
        return shortName;
    }

    /// <summary>Pick up WAVs edited or dropped in while the game is running.</summary>
    public void PollChanges()
    {
        foreach (string animal in ZooIds.AnimalTypes)
            this.Reload(ZooIds.ShortName(animal), announce: true);
    }

    public void Preview(string shortName)
    {
        this.Reload(shortName, announce: false);
        string cue = ZooIds.CueName(shortName);
        if (Game1.soundBank != null && Game1.soundBank.Exists(cue))
        {
            Game1.playSound(cue);
            this.Status = this.T("record.preview", shortName);
        }
        else
        {
            this.Status = this.T("record.invalid", shortName, new { error = "no sound loaded" });
        }
    }

    public bool TryReset(string shortName)
    {
        if (this.Busy)
            return false;
        string baked = this.DefaultPath(shortName);
        if (!File.Exists(baked))
            return false;
        File.Copy(baked, this.WavPath(shortName), overwrite: true);
        this.Reload(shortName, announce: false);
        this.Status = this.T("record.reset", shortName);
        return true;
    }

    public void Record(string shortName)
    {
        if (this.Busy)
        {
            this.Status = this.T("record.busy", this.jobAnimal!);
            return;
        }

        this.jobAnimal = shortName;
        this.jobTemp = Path.Combine(Path.GetTempPath(), $"StardewZoo-{shortName}-{Guid.NewGuid():N}.wav");
        IReadOnlyList<CaptureCommand> commands = CaptureTools.Available(this.jobTemp);
        this.Status = this.T("record.listening", shortName);
        if (commands.Count > 0)
        {
            this.monitor.Log($"Recording {shortName} with {string.Join(", ", commands.Select(c => c.Executable))}.", LogLevel.Debug);
            this.toolJob = Task.Run(() => this.RunTools(commands, this.jobTemp));
        }
        else
        {
            this.monitor.Log($"Recording {shortName}: no ffmpeg/sox found in PATH or {string.Join(", ", CaptureTools.ExtraDirs)}; using the game's microphone.", LogLevel.Debug);
            this.StartMicrophone();
        }
    }

    public void OpenSoundsFolder()
    {
        Directory.CreateDirectory(this.SoundsDir);
        try
        {
            string opener = OperatingSystem.IsMacOS() ? "open" : OperatingSystem.IsWindows() ? "explorer.exe" : "xdg-open";
            var info = new ProcessStartInfo { FileName = opener, UseShellExecute = false };
            info.ArgumentList.Add(this.SoundsDir);
            Process.Start(info)?.Dispose();
        }
        catch (Exception ex)
        {
            this.monitor.Log($"Could not open sounds folder {this.SoundsDir}: {ex.Message}", LogLevel.Warn);
        }
    }

    private async Task<ToolOutcome> RunTools(IReadOnlyList<CaptureCommand> commands, string temp)
    {
        var problems = new List<string>();
        foreach (CaptureCommand command in commands)
        {
            TryDelete(temp);
            CaptureResult result = await CaptureTools.RunAsync(command, ToolTimeout).ConfigureAwait(false);
            string tail = string.Join(" | ", result.Output.Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries).TakeLast(3));
            if (!result.Started || result.TimedOut || result.ExitCode != 0)
            {
                problems.Add($"{command.Name}: {(result.TimedOut ? "timed out" : $"exit {result.ExitCode}")} {tail}");
                continue;
            }
            if (!WavFile.TryRead(temp, out WavInfo? info, out string error))
            {
                problems.Add($"{command.Name}: bad output ({error}) {tail}");
                continue;
            }
            if (WavFile.IsSilent(info!))
                return new ToolOutcome(command.Name, true, $"{command.Name}: peak {info!.Peak}/32767");
            return new ToolOutcome(command.Name, false, $"{info!.Seconds:0.00}s, {info.SampleRate} Hz, peak {info.Peak}");
        }
        return new ToolOutcome(null, false, string.Join("; ", problems));
    }

    private void FinishToolJob()
    {
        ToolOutcome outcome;
        try
        {
            outcome = this.toolJob!.Result;
        }
        catch (Exception ex)
        {
            outcome = new ToolOutcome(null, false, ex.GetBaseException().Message);
        }
        this.toolJob = null;

        if (outcome.Via == null)
        {
            this.monitor.Log($"External recorders failed ({outcome.Detail}); trying the game's microphone.", LogLevel.Warn);
            this.StartMicrophone();
            return;
        }
        this.monitor.Log($"Recorded {this.jobAnimal} via {outcome.Via}: {outcome.Detail}", LogLevel.Debug);
        if (outcome.Silent)
            this.Fail("record.silent", outcome.Detail);
        else
            this.Apply(outcome.Via);
    }

    private void StartMicrophone()
    {
        Microphone? mic = null;
        try
        {
            mic = Microphone.Default ?? Microphone.All.FirstOrDefault();
            if (mic == null)
            {
                this.FailToFolder("no capture device reported by OpenAL");
                return;
            }
            // MonoGame only reports queued samples while a BufferReady handler is attached.
            mic.BufferReady += this.OnMicBuffer;
            mic.Start();
        }
        catch (Exception ex)
        {
            if (mic != null)
                mic.BufferReady -= this.OnMicBuffer;
            this.FailToFolder($"microphone '{mic?.Name}': {ex.Message}");
            return;
        }

        this.capture.Clear();
        this.captureNeeded = mic.GetSampleSizeInBytes(TimeSpan.FromSeconds(CaptureTools.Seconds));
        this.microphone = mic;
        this.micDeadline = DateTime.UtcNow + TimeSpan.FromSeconds(CaptureTools.Seconds) + MicGrace;
        this.monitor.Log($"Recording {this.jobAnimal} from microphone '{mic.Name}' at {mic.SampleRate} Hz.", LogLevel.Debug);
    }

    private void OnMicBuffer(object? sender, EventArgs e) => this.ReadMicrophone();

    private void ReadMicrophone()
    {
        if (this.microphone is not { State: MicrophoneState.Started } mic)
            return;
        var buffer = new byte[8192];
        int read;
        while ((read = mic.GetData(buffer)) > 0)
            this.capture.AddRange(buffer.AsSpan(0, read).ToArray());
    }

    private void TickMicrophone()
    {
        try
        {
            this.ReadMicrophone();
        }
        catch (Exception ex)
        {
            this.monitor.Log($"Microphone read failed: {ex.Message}", LogLevel.Warn);
            this.micDeadline = DateTime.MinValue;
        }
        if (this.capture.Count < this.captureNeeded && DateTime.UtcNow < this.micDeadline)
            return;

        Microphone mic = this.microphone!;
        int rate = mic.SampleRate;
        this.microphone = null;
        mic.BufferReady -= this.OnMicBuffer;
        try { mic.Stop(); } catch (Exception ex) { this.monitor.Log($"Microphone stop failed: {ex.Message}", LogLevel.Trace); }

        byte[] pcm = this.capture.Take(this.captureNeeded).ToArray();
        this.capture.Clear();
        if (pcm.Length < rate / 5 * 2)
        {
            this.Fail("record.silent", $"microphone returned {pcm.Length} bytes");
            return;
        }

        WavFile.Write(this.jobTemp!, pcm, rate);
        if (WavFile.TryRead(this.jobTemp!, out WavInfo? info, out _) && WavFile.IsSilent(info!))
        {
            this.Fail("record.silent", $"microphone peak {info!.Peak}/32767");
            return;
        }
        this.Apply("microphone");
    }

    private void Apply(string via)
    {
        string animal = this.jobAnimal!;
        string temp = this.jobTemp!;
        if (!WavFile.TryRead(temp, out _, out string error))
        {
            this.Fail("record.invalid", error);
            return;
        }
        File.Copy(temp, this.WavPath(animal), overwrite: true);
        this.EndJob();
        this.Reload(animal, announce: false);
        this.monitor.Log($"Saved new {animal} sound via {via}.", LogLevel.Info);
        this.Status = this.T("record.saved", animal);
        Game1.addHUDMessage(new HUDMessage(this.Status, HUDMessage.newQuest_type));
        Game1.playSound(ZooIds.CueName(animal));
    }

    private void FailToFolder(string detail)
    {
        string animal = this.jobAnimal!;
        this.monitor.Log($"Can't record {animal}: {detail}. Opening {this.SoundsDir} so a WAV can be dropped in.", LogLevel.Warn);
        this.EndJob();
        this.OpenSoundsFolder();
        this.Status = this.T("record.drop-wav", animal);
        Game1.addHUDMessage(new HUDMessage(this.Status, HUDMessage.error_type));
    }

    private void Fail(string key, string detail)
    {
        string animal = this.jobAnimal!;
        this.monitor.Log($"Recording {animal} failed ({key}): {detail}. Kept the previous sound.", LogLevel.Warn);
        this.EndJob();
        this.Status = this.T(key, animal, new { error = detail });
        Game1.addHUDMessage(new HUDMessage(this.Status, HUDMessage.error_type));
    }

    private void EndJob()
    {
        if (this.jobTemp != null)
            TryDelete(this.jobTemp);
        this.jobAnimal = null;
        this.jobTemp = null;
        this.toolJob = null;
    }

    /// <summary>Re-register the cue if the WAV changed since it was last loaded.</summary>
    private void Reload(string shortName, bool announce)
    {
        string path = this.WavPath(shortName);
        var file = new FileInfo(path);
        if (!file.Exists)
            return;
        var stamp = (file.LastWriteTimeUtc, file.Length);
        if (this.stamps.TryGetValue(shortName, out var known) && known == stamp)
            return;
        if (announce && DateTime.UtcNow - file.LastWriteTimeUtc < TimeSpan.FromMilliseconds(500))
            return;

        this.stamps[shortName] = stamp;
        bool isCustom = !WavFile.SameContent(path, this.DefaultPath(shortName));
        this.custom[shortName] = isCustom;
        this.SyncSaveFlag(shortName, isCustom);

        if (!WavFile.TryRead(path, out _, out string error))
        {
            this.monitor.Log($"{path} can't be used ({error}); using the default {shortName} sound.", LogLevel.Warn);
            this.RegisterCue(shortName, this.DefaultPath(shortName));
            if (announce)
            {
                this.Status = this.T("record.invalid", shortName, new { error });
                Game1.addHUDMessage(new HUDMessage(this.Status, HUDMessage.error_type));
            }
            return;
        }

        if (this.RegisterCue(shortName, path) && announce)
        {
            this.monitor.Log($"Reloaded {shortName}.wav from the sounds folder.", LogLevel.Info);
            this.Status = this.T("record.reloaded", shortName);
            Game1.addHUDMessage(new HUDMessage(this.Status, HUDMessage.newQuest_type));
        }
    }

    private bool RegisterCue(string shortName, string path)
    {
        if (!File.Exists(path) || Game1.soundBank == null || Game1.audioEngine == null)
            return false;

        try
        {
            SoundEffect effect;
            using (var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                effect = SoundEffect.FromStream(stream, false);

            string cueName = ZooIds.CueName(shortName);
            int category = Game1.audioEngine.GetCategoryIndex("Sound");
            if (Game1.soundBank.Exists(cueName))
            {
                // SetSound releases the previous SoundEffect; every later playSound builds a new Cue from this definition.
                Game1.soundBank.GetCueDefinition(cueName).SetSound(effect, category, false, false);
            }
            else
            {
                var cue = new CueDefinition(cueName, effect, category)
                {
                    instanceLimit = 1,
                    limitBehavior = CueDefinition.LimitBehavior.ReplaceOldest
                };
                Game1.soundBank.AddCue(cue);
            }
            return true;
        }
        catch (Exception ex)
        {
            this.monitor.Log($"Failed to register cue for {shortName} from {path}: {ex.Message}", LogLevel.Warn);
            return false;
        }
    }

    private void SyncSaveFlag(string shortName, bool isCustom)
    {
        string id = "StardewZoo." + shortName;
        if (!isCustom)
            this.save.CustomRecordings.Remove(id);
        else if (!this.save.CustomRecordings.Contains(id))
            this.save.CustomRecordings.Add(id);
    }

    private string T(string key, string shortName, object? extra = null)
    {
        var tokens = new Dictionary<string, object?>
        {
            ["animal"] = this.DisplayName(shortName),
            ["file"] = shortName + ".wav"
        };
        if (extra != null)
        {
            foreach (var prop in extra.GetType().GetProperties())
                tokens[prop.Name] = prop.GetValue(extra);
        }
        return this.helper.Translation.Get(key, tokens);
    }

    private static void TryDelete(string path)
    {
        try
        {
            if (File.Exists(path))
                File.Delete(path);
        }
        catch
        {
            // temp file cleanup is best-effort
        }
    }
}
