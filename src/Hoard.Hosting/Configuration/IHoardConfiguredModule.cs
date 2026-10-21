namespace Hoard.Hosting.Configuration;

public interface IHoardConfiguredModule
{
    void ConfigureOptions(HoardModuleOptions options);
}
