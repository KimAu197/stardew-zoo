using System.Text;

namespace StardewZoo;

/// <summary>Summary of a WAV file, limited to what MonoGame's AudioLoader can play.</summary>
public sealed record WavInfo(int Format, int Channels, int SampleRate, int BitsPerSample, int DataBytes, double Seconds, int Peak);

/// <summary>Reads and writes the small PCM WAV files used for animal cues.</summary>
public static class WavFile
{
    public const int PcmFormat = 1;
    public const int FloatFormat = 3;

    /// <summary>Peak below this (out of 32767) is treated as silence, e.g. a mic blocked by macOS privacy settings.</summary>
    public const int SilencePeak = 200;

    public static void Write(string path, byte[] pcm16Mono, int sampleRate)
    {
        string? dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);
        using var stream = new FileStream(path, FileMode.Create, FileAccess.Write);
        using var writer = new BinaryWriter(stream);
        int dataSize = pcm16Mono.Length & ~1;
        writer.Write(Encoding.ASCII.GetBytes("RIFF"));
        writer.Write(36 + dataSize);
        writer.Write(Encoding.ASCII.GetBytes("WAVE"));
        writer.Write(Encoding.ASCII.GetBytes("fmt "));
        writer.Write(16);
        writer.Write((short)PcmFormat);
        writer.Write((short)1);
        writer.Write(sampleRate);
        writer.Write(sampleRate * 2);
        writer.Write((short)2);
        writer.Write((short)16);
        writer.Write(Encoding.ASCII.GetBytes("data"));
        writer.Write(dataSize);
        writer.Write(pcm16Mono, 0, dataSize);
    }

    /// <summary>Validate a WAV the same way the game's loader will, so a bad file never replaces a working cue.</summary>
    public static bool TryRead(string path, out WavInfo? info, out string error)
    {
        info = null;
        try
        {
            using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
            return TryRead(stream, out info, out error);
        }
        catch (Exception ex)
        {
            error = ex.Message;
            return false;
        }
    }

    public static bool TryRead(Stream stream, out WavInfo? info, out string error)
    {
        info = null;
        error = "";
        try
        {
            using var reader = new BinaryReader(stream, Encoding.ASCII, leaveOpen: true);
            if (stream.Length < 44 || Tag(reader) != "RIFF")
                return Fail("not a RIFF/WAV file", out error);
            reader.ReadInt32();
            if (Tag(reader) != "WAVE")
                return Fail("not a WAVE file", out error);

            int format = 0, channels = 0, rate = 0, bits = 0;
            byte[]? data = null;
            while (data == null)
            {
                if (stream.Length - stream.Position < 8)
                    return Fail("no data chunk", out error);
                string tag = Tag(reader);
                int size = reader.ReadInt32();
                long next = stream.Position + size;
                if (tag == "fmt ")
                {
                    format = reader.ReadInt16();
                    channels = reader.ReadInt16();
                    rate = reader.ReadInt32();
                    reader.ReadInt32();
                    reader.ReadInt16();
                    bits = reader.ReadInt16();
                    stream.Position = next;
                }
                else if (tag == "data")
                {
                    if (size <= 0 || size > stream.Length - stream.Position)
                        return Fail("empty or truncated data chunk", out error);
                    data = reader.ReadBytes(size);
                }
                else
                {
                    stream.Position = next;
                }
            }

            if (format is not (PcmFormat or FloatFormat))
                return Fail($"unsupported WAV encoding {format} (use 16-bit PCM)", out error);
            if (channels is < 1 or > 2)
                return Fail($"unsupported channel count {channels}", out error);
            if (format == PcmFormat && bits is not (8 or 16 or 24))
                return Fail($"unsupported bit depth {bits}", out error);
            if (format == FloatFormat && bits != 32)
                return Fail($"unsupported float bit depth {bits}", out error);
            if (rate is < 8000 or > 48000)
                return Fail($"unsupported sample rate {rate}", out error);

            int frameBytes = channels * bits / 8;
            if (data.Length < frameBytes)
                return Fail("no audio samples", out error);
            double seconds = (double)(data.Length / frameBytes) / rate;
            info = new WavInfo(format, channels, rate, bits, data.Length, seconds, Peak(data, format, bits));
            return true;
        }
        catch (Exception ex)
        {
            error = ex.Message;
            return false;
        }
    }

    public static bool IsSilent(WavInfo info) => info.Peak < SilencePeak;

    /// <summary>Peak absolute amplitude scaled to the 16-bit range.</summary>
    public static int Peak(byte[] data, int format, int bits)
    {
        int peak = 0;
        switch (format, bits)
        {
            case (PcmFormat, 8):
                foreach (byte b in data)
                    peak = Math.Max(peak, Math.Abs((b - 128) * 256));
                break;
            case (PcmFormat, 16):
                for (int i = 0; i + 1 < data.Length; i += 2)
                    peak = Math.Max(peak, Math.Abs((int)BitConverter.ToInt16(data, i)));
                break;
            case (PcmFormat, 24):
                for (int i = 0; i + 2 < data.Length; i += 3)
                    peak = Math.Max(peak, Math.Abs((int)(short)(data[i + 1] | (data[i + 2] << 8))));
                break;
            case (FloatFormat, 32):
                for (int i = 0; i + 3 < data.Length; i += 4)
                    peak = Math.Max(peak, (int)Math.Min(32767, Math.Abs(BitConverter.ToSingle(data, i)) * 32767));
                break;
        }
        return Math.Min(peak, 32767);
    }

    public static bool SameContent(string a, string b)
    {
        try
        {
            var fa = new FileInfo(a);
            var fb = new FileInfo(b);
            if (!fa.Exists || !fb.Exists || fa.Length != fb.Length)
                return false;
            return File.ReadAllBytes(a).AsSpan().SequenceEqual(File.ReadAllBytes(b));
        }
        catch
        {
            return false;
        }
    }

    private static string Tag(BinaryReader reader) => new(reader.ReadChars(4));

    private static bool Fail(string message, out string error)
    {
        error = message;
        return false;
    }
}
