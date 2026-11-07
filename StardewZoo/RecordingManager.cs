using System.Diagnostics;
using Microsoft.Xna.Framework.Audio;
using StardewModdingAPI;
using StardewValley;

namespace StardewZoo;

internal sealed class RecordingManager
{
    private readonly IModHelper helper;
    private readonly IMonitor monitor;
    private FileSystemWatcher? watcher;
    private Microphone? microphone;
    private readonly List<byte> capture = new();
    private int captureNeeded;
    private string? capturingAnimal;
    private DateTime ignoreWatcherUntil = DateTime.MinValue;

    public RecordingManager(IModHelper helper, IMonitor monitor)
    {
        this.helper = helper;
        this.monitor = monitor;
    }

    public string SoundsDir => Path.Combine(this.helper.DirectoryPath, "sounds");

    public string DefaultsDir => Path.Combine(this.SoundsDir, "defaults");

    public void Initialize(ZooSaveData save)
    {
        Directory.CreateDirectory(this.SoundsDir);
        Directory.CreateDirectory(this.DefaultsDir);
        foreach (string animal in ZooIds.AnimalTypes)
        {
            string name = ZooIds.ShortName(animal);
            string live = this.WavPath(name);
            string baked = Path.Combine(this.DefaultsDir, name + ".wav");
            if (!File.Exists(live) && File.Exists(baked))
                File.Copy(baked, live, overwrite: false);
            this.RegisterCue(name);
        }

        this.watcher = new FileSystemWatcher(this.SoundsDir, "*.wav")
        {
            NotifyFilter = NotifyFilters.FileName | NotifyFilters.LastWrite | NotifyFilters.Size,
            EnableRaisingEvents = true
        };
        this.watcher.Changed += this.OnWavDropped;
        this.watcher.Created += this.OnWavDropped;
    }

    public void Tick()
    {
        if (this.microphone == null || this.capturingAnimal == null)
            return;

        var buffer = new byte[4096];
        int read = this.microphone.GetData(buffer);
        if (read > 0)
        {
            this.capture.AddRange(buffer.Take(read));
            this.captureNeeded -= read;
        }

        if (this.captureNeeded > 0 && this.microphone.State == MicrophoneState.Started)
            return;

        this.FinishMicCapture();
    }

    public string WavPath(string shortName) => Path.Combine(this.SoundsDir, shortName + ".wav");

    public bool TryPreview(string shortName)
    {
        this.RegisterCue(shortName);
        Game1.playSound(ZooIds.CueName("StardewZoo." + shortName));
        return true;
    }

    public bool TryReset(string shortName, ZooSaveData save)
    {
        string baked = Path.Combine(this.DefaultsDir, shortName + ".wav");
        if (!File.Exists(baked))
            return false;
        this.ignoreWatcherUntil = DateTime.UtcNow.AddSeconds(1);
        File.Copy(baked, this.WavPath(shortName), overwrite: true);
        save.CustomRecordings.Remove("StardewZoo." + shortName);
        this.RegisterCue(shortName);
        return true;
    }

    public string Record(string shortName, ZooSaveData save)
    {
        string path = this.WavPath(shortName);
        Directory.CreateDirectory(this.SoundsDir);

        string? ffmpeg = Which("ffmpeg");
        if (ffmpeg != null)
        {
            if (this.Run(ffmpeg, $"-y -f avfoundation -i :0 -t 2.5 -ac 1 -ar 22050 \"{path}\""))
                return this.OnRecorded(shortName, save, "ffmpeg");
            this.monitor.Log("ffmpeg avfoundation capture failed; trying sox.", LogLevel.Trace);
        }

        string? rec = Which("rec");
        if (rec != null)
        {
            if (this.Run(rec, $"-r 22050 -c 1 -b 16 \"{path}\" trim 0 2.5"))
                return this.OnRecorded(shortName, save, "sox");
            this.monitor.Log("sox rec failed; trying OpenAL microphone.", LogLevel.Trace);
        }

        Microphone? mic = Microphone.Default;
        if (mic != null)
        {
            this.capture.Clear();
            this.captureNeeded = mic.GetSampleSizeInBytes(TimeSpan.FromSeconds(2.5));
            this.capturingAnimal = shortName;
            this.microphone = mic;
            mic.Start();
            return "mic";
        }

        this.OpenSoundsFolder();
        return "folder";
    }

    public void OpenSoundsFolder()
    {
        Directory.CreateDirectory(this.SoundsDir);
        try
        {
            Process.Start(new ProcessStartInfo { FileName = "open", Arguments = $"\"{this.SoundsDir}\"", UseShellExecute = true });
        }
        catch (Exception ex)
        {
            this.monitor.Log($"Could not open sounds folder: {ex.Message}", LogLevel.Warn);
        }
    }

    public void RegisterCue(string shortName)
    {
        string path = this.WavPath(shortName);
        if (!File.Exists(path) || Game1.soundBank == null || Game1.audioEngine == null)
            return;

        try
        {
            SoundEffect effect;
            using (var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                effect = SoundEffect.FromStream(stream, false);

            string cueName = ZooIds.CueName("StardewZoo." + shortName);
            int category = Game1.audioEngine.GetCategoryIndex("Sound");
            if (Game1.soundBank.Exists(cueName))
            {
                CueDefinition existing = Game1.soundBank.GetCueDefinition(cueName);
                existing.SetSound(effect, category, false, false);
            }
            else
            {
                var cue = new CueDefinition();
                cue.name = cueName;
                cue.instanceLimit = 1;
                cue.limitBehavior = CueDefinition.LimitBehavior.ReplaceOldest;
                cue.SetSound(effect, category, false, false);
                Game1.soundBank.AddCue(cue);
            }
        }
        catch (Exception ex)
        {
            this.monitor.Log($"Failed to register cue for {shortName}: {ex.Message}", LogLevel.Warn);
        }
    }

    private void FinishMicCapture()
    {
        string? animal = this.capturingAnimal;
        try
        {
            this.microphone?.Stop();
        }
        catch
        {
            // ignore
        }

        this.microphone = null;
        this.capturingAnimal = null;
        if (animal == null)
            return;

        int rate = Microphone.Default?.SampleRate ?? 44100;
        WriteWav(this.WavPath(animal), this.capture.ToArray(), rate);
        var save = this.helper.Data.ReadSaveData<ZooSaveData>(ZooSaveData.Key) ?? new ZooSaveData();
        this.OnRecorded(animal, save, "microphone");
        this.helper.Data.WriteSaveData(ZooSaveData.Key, save);
        Game1.addHUDMessage(new HUDMessage(this.helper.Translation.Get("record.saved", new { animal }), HUDMessage.newQuest_type));
    }

    private string OnRecorded(string shortName, ZooSaveData save, string via)
    {
        this.ignoreWatcherUntil = DateTime.UtcNow.AddSeconds(1);
        if (!save.CustomRecordings.Contains("StardewZoo." + shortName))
            save.CustomRecordings.Add("StardewZoo." + shortName);
        this.RegisterCue(shortName);
        this.monitor.Log($"Recorded {shortName} via {via}.", LogLevel.Info);
        return via;
    }

    private void OnWavDropped(object sender, FileSystemEventArgs e)
    {
        if (DateTime.UtcNow < this.ignoreWatcherUntil)
            return;
        string name = Path.GetFileNameWithoutExtension(e.Name ?? "");
        if (string.IsNullOrEmpty(name) || name.Contains(Path.DirectorySeparatorChar))
            return;
        if (!ZooIds.AnimalTypes.Any(id => ZooIds.ShortName(id).Equals(name, StringComparison.OrdinalIgnoreCase)))
            return;
        this.RegisterCue(name);
        var save = this.helper.Data.ReadSaveData<ZooSaveData>(ZooSaveData.Key) ?? new ZooSaveData();
        string id = "StardewZoo." + name;
        if (!save.CustomRecordings.Contains(id))
            save.CustomRecordings.Add(id);
        this.helper.Data.WriteSaveData(ZooSaveData.Key, save);
        this.monitor.Log($"Reloaded dropped recording {name}.wav.", LogLevel.Info);
    }

    private bool Run(string fileName, string arguments)
    {
        try
        {
            using var process = Process.Start(new ProcessStartInfo
            {
                FileName = fileName,
                Arguments = arguments,
                RedirectStandardError = true,
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            });
            if (process == null)
                return false;
            if (!process.WaitForExit(8000))
            {
                try { process.Kill(); } catch { /* ignore */ }
                return false;
            }
            return process.ExitCode == 0 && File.Exists(arguments.Trim().Split(' ').Last().Trim('"'));
        }
        catch (Exception ex)
        {
            this.monitor.Log($"{fileName} failed: {ex.Message}", LogLevel.Trace);
            return false;
        }
    }

    private static string? Which(string name)
    {
        var dirs = (Environment.GetEnvironmentVariable("PATH") ?? "")
            .Split(Path.PathSeparator)
            .Concat(new[] { "/opt/homebrew/bin", "/usr/local/bin" });
        foreach (string dir in dirs)
        {
            string candidate = Path.Combine(dir, name);
            if (File.Exists(candidate))
                return candidate;
        }
        return null;
    }

    private static void WriteWav(string path, byte[] pcm, int sampleRate)
    {
        using var stream = new FileStream(path, FileMode.Create, FileAccess.Write);
        using var writer = new BinaryWriter(stream);
        int dataSize = pcm.Length;
        writer.Write(System.Text.Encoding.ASCII.GetBytes("RIFF"));
        writer.Write(36 + dataSize);
        writer.Write(System.Text.Encoding.ASCII.GetBytes("WAVE"));
        writer.Write(System.Text.Encoding.ASCII.GetBytes("fmt "));
        writer.Write(16);
        writer.Write((short)1);
        writer.Write((short)1);
        writer.Write(sampleRate);
        writer.Write(sampleRate * 2);
        writer.Write((short)2);
        writer.Write((short)16);
        writer.Write(System.Text.Encoding.ASCII.GetBytes("data"));
        writer.Write(dataSize);
        writer.Write(pcm);
    }
}
