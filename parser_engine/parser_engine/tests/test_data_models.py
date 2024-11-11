from datetime import datetime
from parser_engine.models.data_models import *

def test_contributor_data():
    contributor = ContributorData(
        name="John Doe",
        email="john@example.com",
        commits_count=10,
        first_commit_date=datetime.now(),
        last_commit_date=datetime.now(),
        lines_added=100,
        lines_deleted=50
    )
    assert contributor.name == "John Doe"
    assert contributor.commits_count == 10
    assert contributor.lines_added == 100
    assert contributor.lines_deleted == 50

def test_repository_data():
    # Create a minimal directory tree first
    root = DirectoryNode(name="root", path="/")
    tree = DirectoryTree(root=root)
    
    repo = RepositoryData(
        name="test-repo",
        url="https://github.com/test/test-repo",
        primary_language="Python",
        directory_tree=tree,
        languages={"Python": 1000, "JavaScript": 500}
    )
    assert repo.name == "test-repo"
    assert repo.primary_language == "Python"
    assert repo.languages["Python"] == 1000

def test_module_element():
    module = ModuleElement(
        name="test_module",
        path="/src/test_module.py",
        language="Python",
        imports=["os", "sys"],
        size_bytes=1000,
        lines_of_code=100
    )
    assert module.name == "test_module"
    assert module.language == "Python"
    assert "os" in module.imports
    assert module.lines_of_code == 100

def test_file_node():
    file = FileNode(
        name="main.py",
        path="/src/main.py",
        size_bytes=1000,
        last_modified=datetime.now(),
        extension=".py",
        content_type="code",
        language="Python",
        lines_of_code=100
    )
    assert file.name == "main.py"
    assert file.language == "Python"
    assert file.lines_of_code == 100

def test_directory_node():
    directory = DirectoryNode(
        name="src",
        path="/src"
    )
    
    file1 = FileNode(
        name="main.py",
        path="/src/main.py",
        size_bytes=1000,
        last_modified=datetime.now(),
        extension=".py",
        content_type="code"
    )
    
    file2 = FileNode(
        name="utils.py",
        path="/src/utils.py",
        size_bytes=500,
        last_modified=datetime.now(),
        extension=".py",
        content_type="code"
    )
    
    directory.add_file(file1)
    directory.add_file(file2)
    
    assert directory.total_files == 2
    assert directory.total_size_bytes == 1500

def test_directory_tree():
    root = DirectoryNode(name="root", path="/")
    src = DirectoryNode(name="src", path="/src")
    tests = DirectoryNode(name="tests", path="/tests")
    
    main_file = FileNode(
        name="main.py",
        path="/src/main.py",
        size_bytes=1000,
        last_modified=datetime.now(),
        extension=".py",
        content_type="code",
        language="Python",
        lines_of_code=100
    )
    
    test_file = FileNode(
        name="test_main.py",
        path="/tests/test_main.py",
        size_bytes=500,
        last_modified=datetime.now(),
        extension=".py",
        content_type="code",
        language="Python",
        lines_of_code=50
    )
    
    src.add_file(main_file)
    tests.add_file(test_file)
    root.add_directory(src)
    root.add_directory(tests)
    
    tree = DirectoryTree(root=root)
    tree.calculate_stats()
    
    assert tree.total_files == 2
    assert tree.total_size_bytes == 1500
    assert tree.language_stats["Python"] == 150
    assert tree.file_types[".py"] == 2