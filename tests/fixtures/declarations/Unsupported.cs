using Hoard.Abstractions.Modules;

public static class Unsupported
{
    public static ModuleDescriptor Declaration => Consumer.Declaration with
    {
        Id = "INVALID INPUT",
        Version = "not-semver",
        Compatibility = Consumer.Declaration.Compatibility with { HostRange = "" },
        Dependencies = [],
        Capabilities = [],
        Configuration = [],
        Endpoints = [],
        Health = []
    };
}
