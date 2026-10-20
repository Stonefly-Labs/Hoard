namespace FixtureSdk;

public class PrivateModel;
public interface IPrivateConstraint;
public sealed class PrivateAttribute(Type type) : Attribute
{
    public Type Type { get; } = type;
}
