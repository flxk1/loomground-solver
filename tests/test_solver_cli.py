import json

from loomground_solver.__main__ import main

from test_universal_handler import request


def test_manifest_command(capsys):
    assert main(["manifest"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["roles"] == ["verifier"]
    assert "evidence-verification" in output["capabilities"]
    assert "loomground-governance" in output["capabilities"]


def test_verify_command(tmp_path, capsys):
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request()), encoding="utf-8")
    assert main(["verify", str(source)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["accepted"] == ["a"]


def test_bad_request_returns_nonzero(tmp_path, capsys):
    source = tmp_path / "request.json"
    source.write_text("{}", encoding="utf-8")
    assert main(["verify", str(source)]) == 2
    assert "unsupported interoperability protocol" in capsys.readouterr().err


def test_loomground_command(tmp_path, capsys):
    source = tmp_path / "policy.lg"
    source.write_text(
        "actor bot\ngate decide grant bot\ncord bot -> decide\ncord decide -> master\n",
        encoding="utf-8",
    )
    transport = tmp_path / "transport.json"
    transport.write_text(json.dumps({"activations": [{
        "actor": "bot", "source": "decide", "token": {
            "id": "t1", "kind": "act", "risk": "low",
            "party": "deployer", "provenance": []},
    }]}), encoding="utf-8")
    assert main(["loomground", str(source), "--transport", str(transport)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["accepted"] == ["t1"]
