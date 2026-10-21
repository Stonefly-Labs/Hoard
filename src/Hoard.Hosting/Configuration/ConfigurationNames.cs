namespace Hoard.Hosting.Configuration;

internal static class ConfigurationNames
{
    internal static string? Canonical(string? name)
    {
        if (name is not { Length: > 0 and <= 128 }) { return null; }
        var separator = true;
        foreach (var character in name)
        {
            if (char.IsAsciiLetterOrDigit(character)) { separator = false; }
            else if (character is '.' or '-' && !separator) { separator = true; }
            else { return null; }
        }
        return separator ? null : name.ToLowerInvariant();
    }
}
