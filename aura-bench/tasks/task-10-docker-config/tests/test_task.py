import pathlib


def test_dockerfile_exposes_correct_port():
    dockerfile = pathlib.Path(__file__).parent / "Dockerfile"
    content = dockerfile.read_text()
    assert "EXPOSE 8080" in content


def test_dockerfile_starts_correct_entrypoint():
    dockerfile = pathlib.Path(__file__).parent / "Dockerfile"
    content = dockerfile.read_text()
    assert 'CMD ["python", "server.py"]' in content
