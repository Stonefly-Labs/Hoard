namespace Hoard.Hosting.Composition;

public sealed record HoardRequiredCapability(string ModuleId, string CapabilityId, string VersionRange, bool AllowPrerelease);
