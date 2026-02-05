    ## getting the parameters of a module
        cliModule = slicer.modules.swissskullstripper
        n=cliModule.cliModuleLogic().CreateNode()
        for groupIndex in range(n.GetNumberOfParameterGroups()):
            print(f'Group: {n.GetParameterGroupLabel(groupIndex)}')
            for parameterIndex in range(n.GetNumberOfParametersInGroup(groupIndex)):
                print('  {0} [{1}]: {2}'.format(n.GetParameterName(groupIndex, parameterIndex),
                    n.GetParameterTag(groupIndex, parameterIndex),n.GetParameterLabel(groupIndex, parameterIndex)))
        
        for groupIndex in range(n.GetNumberOfParameterGroups()):
            print(f"\nGroup: {n.GetParameterGroupLabel(groupIndex)}")
            for parameterIndex in range(n.GetNumberOfParametersInGroup(groupIndex)):
                print("  name:", n.GetParameterName(groupIndex, parameterIndex),
                    "| label:", n.GetParameterLabel(groupIndex, parameterIndex),
                    "| tag:", n.GetParameterTag(groupIndex, parameterIndex))