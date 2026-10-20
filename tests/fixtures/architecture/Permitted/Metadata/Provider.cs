namespace FixtureMetadata;

public class Provider
{
    public string Describe() => new FixtureSdk.PrivateModel().ToString()!;
}
