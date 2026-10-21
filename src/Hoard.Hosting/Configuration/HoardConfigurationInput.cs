using System.Collections.Immutable;
using System.Text;

namespace Hoard.Hosting.Configuration;

public delegate ValueTask<string> HoardConfigurationFileReader(string path, CancellationToken cancellationToken);
public delegate ValueTask<string?> HoardEnvironmentReader(string name, CancellationToken cancellationToken);

public sealed class HoardConfigurationInput
{
    public HoardConfigurationInput(string defaults, string? explicitFile = null,
        IEnumerable<string>? arguments = null, IReadOnlyDictionary<string, string>? environment = null,
        HoardConfigurationFileReader? readFile = null, HoardEnvironmentReader? readEnvironment = null)
    {
        ArgumentNullException.ThrowIfNull(defaults);
        Defaults = "";
        Arguments = [];
        Environment = ImmutableDictionary<string, string>.Empty;
        ExplicitFile = explicitFile;
        ReadFile = readFile;
        ReadEnvironment = readEnvironment;
        var source = HoardConfigurationSource.Defaults;
        try
        {
            BoundText(defaults, 1024 * 1024);
            Defaults = defaults;
            source = HoardConfigurationSource.CommandLine;
            var copiedArguments = ImmutableArray.CreateBuilder<string>();
            var count = 0;
            var bytes = 0;
            foreach (var argument in arguments ?? [])
            {
                if (++count > 4096) { throw new ConfigurationFailure(HoardConfigurationRule.InputLimit); }
                if (argument is null) { throw new ConfigurationFailure(HoardConfigurationRule.InvalidSource); }
                if (!argument.StartsWith("--hoard", StringComparison.OrdinalIgnoreCase)) { continue; }
                BoundText(argument, 1024 * 1024);
                bytes += Encoding.UTF8.GetByteCount(argument);
                if (bytes > 1024 * 1024) { throw new ConfigurationFailure(HoardConfigurationRule.InputLimit); }
                copiedArguments.Add(argument);
            }
            Arguments = copiedArguments.ToImmutable();
            source = HoardConfigurationSource.Environment;
            var copiedEnvironment = ImmutableDictionary.CreateBuilder<string, string>(StringComparer.Ordinal);
            count = 0;
            foreach (var entry in environment ?? new Dictionary<string, string>())
            {
                if (++count > 4096) { throw new ConfigurationFailure(HoardConfigurationRule.InputLimit); }
                if (entry.Key is not { Length: > 0 and <= 128 }
                    || !(char.IsAsciiLetter(entry.Key[0]) || entry.Key[0] == '_')
                    || entry.Key.Any(character => !char.IsAsciiLetterOrDigit(character) && character != '_'))
                { continue; }
                if (entry.Value is null) { throw new ConfigurationFailure(HoardConfigurationRule.InvalidSource); }
                if (entry.Key.Equals("HOARD_CONFIG", StringComparison.OrdinalIgnoreCase))
                { BoundText(entry.Value, 1024 * 1024); }
                copiedEnvironment.Add(entry.Key, entry.Value);
            }
            Environment = copiedEnvironment.ToImmutable();
        }
        catch (Exception error)
        {
            InputError = error is ConfigurationFailure failure ? failure.Rule : HoardConfigurationRule.InvalidSource;
            InputErrorSource = source;
        }
    }
    private static void BoundText(string text, int maximum)
    {
        if (text.Length > maximum || new UTF8Encoding(false, true).GetByteCount(text) > maximum)
        { throw new ConfigurationFailure(HoardConfigurationRule.InputLimit); }
    }
    internal HoardConfigurationRule? InputError { get; }
    internal HoardConfigurationSource InputErrorSource { get; }
    internal string Defaults { get; }
    internal string? ExplicitFile { get; }
    internal ImmutableArray<string> Arguments { get; }
    internal ImmutableDictionary<string, string> Environment { get; }
    internal HoardConfigurationFileReader? ReadFile { get; }
    internal HoardEnvironmentReader? ReadEnvironment { get; }
    public override string ToString() => "Hoard configuration input (private)";
}
