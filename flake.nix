{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = {nixpkgs, ...}:
    let
      forAllSystems = function:
        nixpkgs.lib.genAttrs [
          "x86_64-linux"
          "aarch64-linux"
        ] (system:
          function (import nixpkgs {
            inherit system;
            overlays = [
            ];
          }));
    in {
      devShells = forAllSystems (pkgs:
        let
          nodejs = pkgs.nodejs_22;
        in {
          default = pkgs.mkShell {
            buildInputs = [
              (pkgs.python3.withPackages (python-pkgs: [
                # select Python packages here
                python-pkgs.beautifulsoup4
                python-pkgs.requests
                python-pkgs.jinja2
                python-pkgs.python-dotenv
                python-pkgs.numpy
                python-pkgs.pandas
                python-pkgs.pillow
                python-pkgs.scikit-learn
              ]))
              pkgs.netlify-cli
              #nodejs
              #(pkgs.netlify-cli.override (old: {
              #   inherit nodejs;
              #}))
            ];
            shellHook = ''
            '';
          };
        });
    };
}
