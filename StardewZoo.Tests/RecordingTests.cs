using System.Text;
using StardewZoo;
using Xunit;

public class RecordingTests : IDisposable
{
    private readonly string dir = Path.Combine(Path.GetTempPath(), "StardewZooTests-" + Guid.NewGuid().ToString("N"));

    public RecordingTests() => Directory.CreateDirectory(this.dir);

    public void Dispose() => Directory.Delete(this.dir, recursive: true);

    private string TempWav(string name = "a.wav") => Path.Combine(this.dir, name);

    private static byte[] Tone(int samples, short amplitude)
    {
        var pcm = new byte[samples * 2];
        for (int i = 0; i < samples; i++)
            BitConverter.GetBytes((short)(amplitude * Math.Sin(i * 0.1))).CopyTo(pcm, i * 2);
        return pcm;
    }

    private static byte[] RawWav(int format, int channels, int rate, int bits, byte[] data, bool listChunk = false)
    {
        using var ms = new MemoryStream();
        using var w = new BinaryWriter(ms);
        byte[] list = Encoding.ASCII.GetBytes("INFOISFT\u000e\0\0\0Lavf60.16.100\0");
        int riffSize = 4 + 24 + (listChunk ? 8 + list.Length : 0) + 8 + data.Length;
        w.Write(Encoding.ASCII.GetBytes("RIFF"));
        w.Write(riffSize);
        w.Write(Encoding.ASCII.GetBytes("WAVE"));
        w.Write(Encoding.ASCII.GetBytes("fmt "));
        w.Write(16);
        w.Write((short)format);
        w.Write((short)channels);
        w.Write(rate);
        w.Write(rate * channels * bits / 8);
        w.Write((short)(channels * bits / 8));
        w.Write((short)bits);
        if (listChunk)
        {
            w.Write(Encoding.ASCII.GetBytes("LIST"));
            w.Write(list.Length);
            w.Write(list);
        }
        w.Write(Encoding.ASCII.GetBytes("data"));
        w.Write(data.Length);
        w.Write(data);
        return ms.ToArray();
    }

    [Fact]
    public void Write_ProducesLoadable16BitMonoPcm()
    {
        string path = this.TempWav();
        WavFile.Write(path, Tone(44100, 12000), 44100);

        Assert.True(WavFile.TryRead(path, out WavInfo? info, out string error), error);
        Assert.Equal(WavFile.PcmFormat, info!.Format);
        Assert.Equal(1, info.Channels);
        Assert.Equal(16, info.BitsPerSample);
        Assert.Equal(44100, info.SampleRate);
        Assert.Equal(1.0, info.Seconds, 3);
        Assert.False(WavFile.IsSilent(info));
    }

    [Fact]
    public void Silence_IsDetected()
    {
        string path = this.TempWav();
        WavFile.Write(path, new byte[44100], 44100);
        Assert.True(WavFile.TryRead(path, out WavInfo? info, out _));
        Assert.True(WavFile.IsSilent(info!));
    }

    [Fact]
    public void FfmpegStyleListChunk_IsSkipped()
    {
        string path = this.TempWav();
        File.WriteAllBytes(path, RawWav(1, 1, 44100, 16, Tone(1000, 9000), listChunk: true));
        Assert.True(WavFile.TryRead(path, out WavInfo? info, out string error), error);
        Assert.Equal(2000, info!.DataBytes);
    }

    [Fact]
    public void FloatWav_IsAcceptedAndPeakScaled()
    {
        var data = new byte[400];
        for (int i = 0; i < 100; i++)
            BitConverter.GetBytes(i == 50 ? 0.5f : 0f).CopyTo(data, i * 4);
        string path = this.TempWav();
        File.WriteAllBytes(path, RawWav(3, 1, 48000, 32, data));
        Assert.True(WavFile.TryRead(path, out WavInfo? info, out string error), error);
        Assert.InRange(info!.Peak, 16000, 16500);
    }

    [Theory]
    [InlineData(2, 1, 44100, 4)]   // ADPCM
    [InlineData(1, 6, 44100, 16)]  // 5.1
    [InlineData(1, 1, 96000, 16)]  // sample rate too high
    [InlineData(1, 1, 44100, 32)]  // 32-bit integer PCM
    public void UnsupportedFormats_AreRejected(int format, int channels, int rate, int bits)
    {
        string path = this.TempWav();
        File.WriteAllBytes(path, RawWav(format, channels, rate, bits, new byte[4096]));
        Assert.False(WavFile.TryRead(path, out _, out string error));
        Assert.NotEmpty(error);
    }

    [Fact]
    public void TruncatedOrEmptyFiles_AreRejected()
    {
        string empty = this.TempWav("empty.wav");
        File.WriteAllBytes(empty, Array.Empty<byte>());
        Assert.False(WavFile.TryRead(empty, out _, out _));

        string headerOnly = this.TempWav("header.wav");
        File.WriteAllBytes(headerOnly, RawWav(1, 1, 44100, 16, Array.Empty<byte>()));
        Assert.False(WavFile.TryRead(headerOnly, out _, out _));

        string text = this.TempWav("text.wav");
        File.WriteAllText(text, new string('x', 100));
        Assert.False(WavFile.TryRead(text, out _, out _));

        Assert.False(WavFile.TryRead(this.TempWav("missing.wav"), out _, out _));
    }

    [Fact]
    public void ShippedDefaults_AreAllLoadableAndAudible()
    {
        string defaults = Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "StardewZoo", "sounds", "defaults");
        foreach (string animal in ZooIds.AnimalTypes)
        {
            string path = Path.Combine(defaults, ZooIds.ShortName(animal) + ".wav");
            Assert.True(WavFile.TryRead(path, out WavInfo? info, out string error), $"{path}: {error}");
            Assert.False(WavFile.IsSilent(info!), path);
        }
    }

    [Fact]
    public void SameContent_ComparesBytes()
    {
        string a = this.TempWav("a.wav"), b = this.TempWav("b.wav"), c = this.TempWav("c.wav");
        WavFile.Write(a, Tone(100, 5000), 22050);
        WavFile.Write(b, Tone(100, 5000), 22050);
        WavFile.Write(c, Tone(100, 6000), 22050);
        Assert.True(WavFile.SameContent(a, b));
        Assert.False(WavFile.SameContent(a, c));
        Assert.False(WavFile.SameContent(a, this.TempWav("missing.wav")));
    }

    [Fact]
    public void Find_SearchesExtraDirsWhenPathIsMinimal()
    {
        string bin = Path.Combine(this.dir, "homebrew", "bin");
        Directory.CreateDirectory(bin);
        File.WriteAllText(Path.Combine(bin, "ffmpeg"), "");

        Assert.Null(CaptureTools.Find("ffmpeg", "/usr/bin:/bin", Array.Empty<string>()));
        Assert.Equal(Path.Combine(bin, "ffmpeg"), CaptureTools.Find("ffmpeg", "/usr/bin:/bin", new[] { bin }));
        Assert.Equal(Path.Combine(bin, "ffmpeg"), CaptureTools.Find("ffmpeg", bin, Array.Empty<string>()));
        Assert.Contains("/opt/homebrew/bin", CaptureTools.ExtraDirs);
        Assert.Contains("/usr/local/bin", CaptureTools.ExtraDirs);
    }

    [Fact]
    public void FfmpegCommand_Forces16BitMonoPcmAndKeepsPathWithSpacesAsOneArgument()
    {
        string output = "/Users/x/Library/Application Support/Stardew Valley/Mods/StardewZoo/sounds/Lion.wav";
        CaptureCommand cmd = CaptureTools.Ffmpeg("/opt/homebrew/bin/ffmpeg", output);
        string joined = string.Join(" ", cmd.Arguments);

        Assert.Contains("-acodec pcm_s16le", joined);
        Assert.Contains("-ar 44100", joined);
        Assert.Contains("-ac 1", joined);
        Assert.Contains("-t 2.5", joined);
        Assert.Equal(output, cmd.Arguments[^1]);
        if (OperatingSystem.IsMacOS())
            Assert.Contains("-f avfoundation -i :0", joined);
    }

    [Fact]
    public void SoxCommand_PutsTrimAfterOutputFile()
    {
        CaptureCommand cmd = CaptureTools.SoxRec("/usr/local/bin/rec", "/tmp/out file.wav");
        int output = cmd.Arguments.ToList().IndexOf("/tmp/out file.wav");
        Assert.True(output > 0);
        Assert.Equal(new[] { "trim", "0", "2.5" }, cmd.Arguments.Skip(output + 1));
        Assert.Contains("signed-integer", cmd.Arguments);
    }

    [Fact]
    public async Task RunAsync_ReportsExitCodeOutputAndMissingExecutable()
    {
        CaptureResult ok = await CaptureTools.RunAsync(new CaptureCommand("sh", "/bin/sh", new[] { "-c", "echo hello >&2; exit 3" }), TimeSpan.FromSeconds(10));
        Assert.True(ok.Started);
        Assert.Equal(3, ok.ExitCode);
        Assert.Contains("hello", ok.Output);

        CaptureResult missing = await CaptureTools.RunAsync(new CaptureCommand("nope", "/definitely/not/here", Array.Empty<string>()), TimeSpan.FromSeconds(5));
        Assert.False(missing.Started);
    }

    [Fact]
    public async Task RunAsync_KillsHungRecorder()
    {
        CaptureResult result = await CaptureTools.RunAsync(new CaptureCommand("sleep", "/bin/sleep", new[] { "30" }), TimeSpan.FromMilliseconds(300));
        Assert.True(result.TimedOut);
    }

    [Fact]
    public async Task RunAsync_WritesWavLikeARecorderWould()
    {
        string src = this.TempWav("src.wav");
        string dst = this.TempWav("dst with space.wav");
        WavFile.Write(src, Tone(22050, 8000), 22050);
        CaptureResult result = await CaptureTools.RunAsync(new CaptureCommand("cp", "/bin/cp", new[] { src, dst }), TimeSpan.FromSeconds(5));
        Assert.Equal(0, result.ExitCode);
        Assert.True(WavFile.TryRead(dst, out WavInfo? info, out _));
        Assert.False(WavFile.IsSilent(info!));
    }
}
