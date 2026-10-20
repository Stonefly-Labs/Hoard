using Hoard.Tests;

namespace Hoard.Foundation.Tests;

public class DeclarationContractTests
{
    [Theory]
    [InlineData("Valid", "")]
    [InlineData("Unsupported", "")]
    [InlineData("MissingRequired", "CS9035")]
    [InlineData("InitOnly", "CS8852")]
    [InlineData("MutableCollection", "CS0029")]
    public void Public_consumers_enforce_declaration_shape(string name, string diagnostic)
    {
        var proof = FoundationEvidence.Load().GetProperty("declarations").GetProperty(name);
        Assert.Equal(diagnostic.Length == 0, proof.GetProperty("success").GetBoolean());
        if (diagnostic.Length != 0)
        {
            Assert.Contains(diagnostic, proof.GetProperty("output").GetString());
        }
    }
}
