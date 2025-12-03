{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  buildInputs = with pkgs; [
    (python311.withPackages (
      ps: with ps; [
        grpcio-tools
      ]
    ))
    gnumake
  ];

  shellHook = ''
    if [[ -d venv ]]; then
        source venv/bin/activate
    else
        make setup
        source venv/bin/activate
    fi
  '';
}
