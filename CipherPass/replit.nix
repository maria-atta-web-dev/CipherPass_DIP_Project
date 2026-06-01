{pkgs}: {
  deps = [
    pkgs.dbus
    pkgs.gcc
    pkgs.libxkbcommon
    pkgs.glib
    pkgs.libGL
    pkgs.zlib
    pkgs.freetype
    pkgs.fontconfig
    pkgs.xorg.libXrandr
    pkgs.xorg.libXext
    pkgs.xorg.libXrender
    pkgs.xorg.libXi
    pkgs.xorg.xcbutilwm
    pkgs.xorg.xcbutilrenderutil
    pkgs.xorg.xcbutilkeysyms
    pkgs.xorg.xcbutilimage
    pkgs.xorg.xcbutil
    pkgs.xorg.libxcb
    pkgs.xorg.libX11
    pkgs.unzip
  ];
}
