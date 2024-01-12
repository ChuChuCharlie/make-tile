# MakeTile
A 3D printable dungeon tile creator addon for Blender 3.2+

This is an update that provides compatibility with Blender 3.2 and 4. There are no new features. The code changes make it incompatible with older versions of Blender, you will need the original MakeTile, that this is a fork of, by richyrose (https://github.com/richeyrose/make-tile). Any updates to the source I will try and reflect in this version.

**Installation**
Download the latest .zip from https://github.com/ChuChuCharlie/make-tile/releases, this contains additonal .blend files for assets used. In Blender go to Edit->Preferences the Add-ons and Install.

Once loaded, expand the newly added Add-on and click Restore Default Materials. This is necessary for the materials to be loaded. Restart Blender for good measure. Refer to the original documentation for usage.

**Original readme**

A series of videos on how to use MakeTile can be found on my YouTube channel here https://www.youtube.com/channel/UC7TUNzEtli-sQRj5anS7DFA

Documentation can be found at https://maketile.readthedocs.io/en/latest/

Make sure you download the latest release by going to https://github.com/ChuChuCharlie/make-tile/releases and then downloading the latest MakeTile.zip file as this contains a .blend file with assets that are necessary for MakeTile to work.

MakeTile ran a succesful Kickstarter in 2020 and you can find all the updates here https://www.kickstarter.com/projects/modmodterrain/maketile-custom-dungeon-tile-creator.

MakeTile was available for a time on Gumroad after the Kickstarter finished. However since I can't guarantee to keep it up to date with the latest version of Blender at the moment I have released the latest version here.

The asset manager is now deprecated as Blender now comes with its own internal one.

# Feature Roadmap
Features tagged **Community** will be available for download from this public repository.

Features tagged **Core** will be available to Kickstarter backers who have supported the core tier.

Features tagged **Plus** will be available to Kickstarter backers who have supported the plus tier.

## Phase 1
- [x] Basic user documentation - Community - Complete - Released
- [x] Prototype code refactor, cleanup and documentation - Community - Complete - Released
- [x] Implement toggleable base sockets - Community - Complete - Released
- [x] Implement pegs so tiles can be stacked - Community - Complete - Released
- [x] Optimise tile generators to use bmesh module - Community - Complete - Released

## Phase 2
- [x] Optimise existing materials - Community - In Progress. Paused
- [x] OpenLOCK I, L, O, T, X column tiles - Community - Complete - Released
- [x] OpenLOCK roof pack 1 - Plus - Complete - Released
- [x] Basic version of asset manager - Core - Complete - Released
- [x] Static window, door and stair models - Core - Released
- [x] OpenLOCK S-Walls pack - Plus
- [x] Additional user documentation - Community

## Phase 3
- [ ] OpenLOCK roof and chimney pack 2 - Plus
- [ ] OpenLOCK secondary and weird walls and floors pack - Plus
- [ ] OpenLOCK roof and chimney pack 3 - Plus

## Phase 4
- [ ] Additional materials pack pt. 1 - Plus
- [ ] Additional materials pack pt. 2 - Plus
- [ ] Windows and doors generator - Plus
- [ ] Stairs generator - Plus
- [ ] OpenLOCK compatible T and X wall tiles - Core

## Licensing and copyright info
MakeTile is licensed under the GNU GPLv3 http://www.gnu.org/licenses/

All objects, materials and images bundled with MakeTile in the form of a .blend file are copyright ModMod Terrain Ltd under the [Creative Commons-Attribution-Non-Commercial](https://creativecommons.org/licenses/by-nc/4.0/) license unless otherwise noted.

Current exceptions are any meshes required for the generation of OpenLOCK tiles which are copyright Printablescenery under the [Creative Commons-Attribution-Non-Commercial](https://creativecommons.org/licenses/by-nc/4.0/) license

If you would like to use the materials or meshes bundled with MakeTile for commercial purposes and have backed MakeTile through Kickstarter or purchased it on Gumroad please [contact me](https://github.com/richeyrose/make-tile/issues) by raising an issue for a free commercial license.

If you would like to produce OpenLOCK compatible tiles for commercial purposes please contact [Printablescenery]( https://www.printablescenery.com) for a free commercial license
