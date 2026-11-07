using System.Diagnostics;
using System.Text;

namespace StardewZoo;

public sealed record CaptureCommand(string Name, string Executable, IReadOnlyList<string> Arguments);

public sealed record CaptureResult(bool Started, int ExitCode, bool TimedOut, string Output);

/// <summary>Finds and runs external recorders (ffmpeg, sox). The game process does not inherit the shell PATH, so Homebrew paths are searched explicitly.</summary>
public static class CaptureTools
{
    public const double Seconds = 2.5;
    public const int SampleRate = 44100;

    public static readonly IReadOnlyList<string> ExtraDirs = new[] { "/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin", "/usr/bin" };

    public static string? Find(string name, string? pathEnv, IEnumerable<string>? extraDirs = null)
    {
        IEnumerable<string> dirs = (pathEnv ?? "")
            .Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries)
            .Concat(extraDirs ?? ExtraDirs);
        foreach (string dir in dirs)
        {
            string candidate = Path.Combine(dir, name);
            if (File.Exists(candidate))
                return candidate;
        }
        return null;
    }

    public static IReadOnlyList<CaptureCommand> Available(string outputPath)
    {
        string? path = Environment.GetEnvironmentVariable("PATH");
        var commands = new List<CaptureCommand>();
        if (Find("ffmpeg", path) is { } ffmpeg)
            commands.Add(Ffmpeg(ffmpeg, outputPath));
        if (Find("rec", path) is { } rec)
            commands.Add(SoxRec(rec, outputPath));
        return commands;
    }

    public static CaptureCommand Ffmpeg(string exe, string outputPath)
    {
        string device = OperatingSystem.IsMacOS() ? "avfoundation" : OperatingSystem.IsWindows() ? "dshow" : "pulse";
        string input = OperatingSystem.IsMacOS() ? ":0" : "default";
        return new CaptureCommand("ffmpeg", exe, new[]
        {
            "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
            "-f", device, "-i", input,
            "-t", Seconds.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture),
            "-vn", "-acodec", "pcm_s16le", "-ar", SampleRate.ToString(), "-ac", "1",
            outputPath
        });
    }

    public static CaptureCommand SoxRec(string exe, string outputPath)
    {
        return new CaptureCommand("sox", exe, new[]
        {
            "-q", "-r", SampleRate.ToString(), "-c", "1", "-b", "16", "-e", "signed-integer",
            outputPath,
            "trim", "0", Seconds.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture)
        });
    }

    /// <summary>Run a command without blocking the caller; stdout/stderr are drained so a chatty tool can't deadlock.</summary>
    public static async Task<CaptureResult> RunAsync(CaptureCommand command, TimeSpan timeout)
    {
        var info = new ProcessStartInfo
        {
            FileName = command.Executable,
            RedirectStandardError = true,
            RedirectStandardOutput = true,
            RedirectStandardInput = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };
        foreach (string arg in command.Arguments)
            info.ArgumentList.Add(arg);

        var output = new StringBuilder();
        Process? process;
        try
        {
            process = Process.Start(info);
        }
        catch (Exception ex)
        {
            return new CaptureResult(false, -1, false, ex.Message);
        }
        if (process == null)
            return new CaptureResult(false, -1, false, "process did not start");

        using (process)
        {
            process.OutputDataReceived += (_, e) => { if (e.Data != null) lock (output) output.AppendLine(e.Data); };
            process.ErrorDataReceived += (_, e) => { if (e.Data != null) lock (output) output.AppendLine(e.Data); };
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();
            process.StandardInput.Close();

            using var cts = new CancellationTokenSource(timeout);
            try
            {
                await process.WaitForExitAsync(cts.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                try { process.Kill(entireProcessTree: true); } catch { /* already gone */ }
                lock (output)
                    return new CaptureResult(true, -1, true, output.ToString());
            }
            process.WaitForExit();
            lock (output)
                return new CaptureResult(true, process.ExitCode, false, output.ToString());
        }
    }
}
