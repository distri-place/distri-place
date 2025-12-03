{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python311
    gnumake
    stdenv.cc.cc.lib
  ];

  shellHook = ''
    export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
    if [[ -d venv ]]; then
        source venv/bin/activate
    else
        make setup
        source venv/bin/activate
    fi
  '';
}
