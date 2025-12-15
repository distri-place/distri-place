{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  buildInputs = with pkgs; [
    gnumake
    pandoc
    mermaid-filter
    texlive.combined.scheme-full
  ];
}
