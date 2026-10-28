using System.Reflection;
using Xunit.Sdk;

namespace Hoard.Fixtures.Conformance.Consumer;

[AttributeUsage(AttributeTargets.Method, AllowMultiple = true)]
internal sealed class MetadataBindingDataAttribute(params object[] arguments) : DataAttribute
{
    public override IEnumerable<object[]> GetData(MethodInfo testMethod)
    {
#if HOARD_METADATA_CONTRIBUTOR
        string[] bindings = [ContributorBindingFactory.BindingId];
#else
        string[] bindings = ["memory", "sqlite"];
#endif
        foreach (var binding in bindings) { yield return [binding, .. arguments]; }
    }
}
