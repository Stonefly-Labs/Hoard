using System.Collections.Generic;
using Hoard.Abstractions.Modules;

public static class MutableCollection
{
    public static ModuleDescriptor Declaration => Consumer.Declaration with
    {
        Dependencies = new List<ModuleDependency>()
    };
}
