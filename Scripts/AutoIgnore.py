import os
import sys
import posixpath
import subprocess

# Configuration
c_szIgnore = ".gitignore"
c_szBlockHeader = "# [BEGIN AUTO IGNORE]"
c_szBlockFooter = "# [END AUTO IGNORE]"

# Ignoring rules
class CDefaultPredicate:
    def __init__(self, szRootPath):
        pass
        
    def Ignore(self, szFilePath):
        return os.path.islink(szFilePath)

# Logic
class CIgnoreTree:
    def __init__(self, szRootPath):
        self.m_szRootPath = szRootPath
        self.m_arrFiles = []
        self.m_szIgnorePath = os.path.join(self.m_szRootPath, c_szIgnore)
        self.m_linesBefore = []
        self.m_linesInside = []
        self.m_linesAfter = []
        
        pCurrentList = [self.m_linesBefore]
        
        with open(self.m_szIgnorePath, 'r') as f:
            for szLine in f:
                if szLine.startswith(c_szBlockHeader):
                    pCurrentList = [self.m_linesInside]
                elif szLine.startswith(c_szBlockFooter):
                    pCurrentList = [self.m_linesAfter]
                else:
                    pCurrentList[0].append(szLine.rstrip())
    
    def __del__(self):
        with open(self.m_szIgnorePath, 'w') as f:
            for szLine in self.m_linesBefore:
                print(szLine, file=f)
            
            if self.m_linesInside:
                print(c_szBlockHeader, file=f)
                for szLine in self.m_linesInside:
                    print(szLine, file=f)
                print(c_szBlockFooter, file=f)
                
            for szLine in self.m_linesAfter:
                print(szLine, file=f)
    
    def Run(self):
        cPredicate = CDefaultPredicate(self.m_szRootPath)

        arrNewIgnoreList = []
        
        # For the entries in the current ignore list, decide if the should remain
        for szLine in self.m_linesInside:
            if szLine in arrNewIgnoreList:
                continue
                
            szFile = os.path.join(self.m_szRootPath, szLine.lstrip(posixpath.sep).replace(posixpath.sep, os.sep))
            if cPredicate.Ignore(szFile):
                arrNewIgnoreList.append(szLine)
                
        # For files in directory, decide if they must be in the ignore list
        for szFile in self.m_arrFiles:
            szLine = posixpath.sep + os.path.relpath(szFile, self.m_szRootPath).replace(os.sep, posixpath.sep)
        
            if szLine in arrNewIgnoreList:
                continue
            
            if cPredicate.Ignore(szFile):
                arrNewIgnoreList.append(szLine)
                
        # Report changes
        m_arrInsertions = []
        m_arrDeletions  = []
        
        for szLine in arrNewIgnoreList:
            if szLine not in self.m_linesInside:
                m_arrInsertions.append(szLine)
                
        for szLine in self.m_linesInside:
            if szLine not in arrNewIgnoreList:
                m_arrDeletions.append(szLine)
        
        bChanges = False
        
        print(self.m_szIgnorePath + ":")
        if len(m_arrInsertions) == 0 and len(m_arrDeletions) == 0:
            print("\tNo changes")
        else:
            bChanges = True
            print("\tAdditions:" + "".join(["\n\t\t" + line for line in m_arrInsertions]))
            print("\tDeletions:" + "".join(["\n\t\t" + line for line in m_arrDeletions]))
            
        # Update the file
        self.m_linesInside = arrNewIgnoreList
        
        return bChanges
    
def traverseDir(szDirRoot, szGitMetaDir, currentTree, arrIgnoreTrees):
    # Skip .git directory
    if szDirRoot.startswith(szGitMetaDir):
            return
            
    # If a gitignore is present, then prune the current tree
    if c_szIgnore in os.listdir(szDirRoot):
        currentTree = CIgnoreTree(szDirRoot)
        arrIgnoreTrees.append( currentTree )
        
    for entry in os.scandir(szDirRoot):
        if entry.is_dir():                          
            traverseDir(entry.path, szGitMetaDir, currentTree, arrIgnoreTrees)
        elif currentTree and entry.is_file():
            # Add all the subfiles to the current tree
            currentTree.m_arrFiles.append(entry.path)
    
def main():
    # Get the top directory of the GIT repo
    cGitRootSubp = subprocess.run(['git', 'rev-parse', '--show-toplevel'], check=False, capture_output=True)
    if 0 != cGitRootSubp.returncode:
        szGitErr = cGitRootSubp.stderr.decode('ASCII')
        print("Failed to get root directory of GIT repository:")
        print(szGitErr)
        return cGitRootSubp.returncode
        
    szGitRootDir = cGitRootSubp.stdout.decode('ASCII').strip().replace(posixpath.sep, os.sep)
    szGitMetaDir = os.path.join(szGitRootDir, ".git")
        
    # Traverse the repo tree and subdivide by gitignores
    arrIgnoreTrees = []
    traverseDir(szGitRootDir, szGitMetaDir, None, arrIgnoreTrees)

    # Process each tree
    bChanges = False
    for cTree in arrIgnoreTrees:
        bChanges = bChanges or cTree.Run()
    
    return int(bChanges)
    
if __name__ == '__main__':
    sys.exit(main())