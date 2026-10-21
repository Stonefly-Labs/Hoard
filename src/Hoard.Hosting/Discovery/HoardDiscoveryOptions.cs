namespace Hoard.Hosting.Discovery;

public enum HoardDiscoveryExposure { Unconfigured, LocalLoopback, SecuredNetwork }

public sealed record HoardDiscoveryOptions
{
    public HoardDiscoveryExposure Exposure { get; init; }
    public string ManagementReadPolicy { get; init; } = "Hoard.Management.Read";
    public bool DirectLocalNoProxy { get; init; }
    public bool TrustedProxyTlsTermination { get; init; }
    public TimeSpan Deadline { get; init; } = TimeSpan.FromSeconds(2);
    public int MaximumResponseBytes { get; init; } = 4 * 1024 * 1024;
    public TimeProvider TimeProvider { get; init; } = TimeProvider.System;
}

public sealed class HoardDiscoverySetupException : InvalidOperationException
{
    public HoardDiscoverySetupException() : base("Invalid discovery metadata, ownership, limits or protection. Correct the explicit host catalog and restart.") { }
}
