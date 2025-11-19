{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python311
    gnumake
    python311Packages.grpcio-tools
  ];

  shellHook = ''
    make setup
    if [[ -d venv ]]; then
    source venv/bin/activate
    fi
  '';
}
