# Changelog

# v0.1.0 - Significant Changes


## New Features

* On first run, you'll be asked to enter the game install directory, and the editor will mine the game data as well as required thumbnail images to be used in the editor. You can chose not to, but you will lose the ability to use the catalog explorer, see icons for objects, spells and artifacts, and you will not have sid's fill dropdowns in editor fields.

* All dropdowns now have names and thumbnails of list items for a better user experience.

* Editor fields now correctly narrow down which sid types are allowed in which field instead of containing a list of everything in the game.

* Properly implemented bonus selection in template settings.

* Catalog explorer now shows detailed content about artifacts, spells, resources and map objects.

## Improvements

* Faction selection fields are now proper dropdowns instead of free fields.

* Road and Biome selection are now type-aware and will correctly display relevant options in the dropdowns based on which type was selected.

* Changed the layout split direction for catalog explorer so its easier to use (list on left, details on right instead of top/bottom split)

* Improved UX for content items elements on mandatory content lists and content limits.

* Improved UI load times.


## Bugfixes

* Removed empty type option from road types.

* Value overrides tab on template editor is now scrollable and won't cause super long dialog windows that overflow the screen if there are too many overrides.
---

# v0.0.7

## New Features

* Windows executable is now released as a zip file that also contains catalog.json and images.

* Save zone positions in the editor canvas to the thumbnail exif so next time it is opened we can restore the same positions in editor (without adding junk to the template file)


## Bugfixes

* Fixed catalog explorer and related autofills not working on windows executable.



# v0.0.6

## New features

* Added a context menu on the zone layout canvas that has various options for aligning selected zones:
    * Align Horizontally
    * Align Vertically
    * Align in a Line
    * Align in a Circle
    * Set Equal Distance
    * Set Equal Distance (X)
    * Set Equal Distance (Y)
* Item and spell data now included in the catalog viewer.

* Added items and spells to the catalog explorer.

* You can now add multiple connections between same two zones.

* Connection type between zones can now be changed in the inspector widget.

* Added changelog to the "about" window.

## Bugfixes

* Fixed a bug that caused connections to be retained in template files and thumbnail images when a zone that has connections was deleted.

* Fixed a bug that caused zone richness colors (empty, blue, golden) in the thumbnail to be incorrectly set when zones had equal values.
  * The way colors were set was they were sorted by value then split 30/40/30 and assigned colors. The correct way was to set threshold between max/min zone values and color according to that so zones with equal values did not get assigned to different buckets.

* In template -> template settings -> global bans, item and spell id's are now correctly listed (instead of listing every SID in catalog)

* Fixed a problem with roads widget in a zone going invisible.

* Fixed dropdowns and initial values when creating a road, now you can select a connection name from dropdown.

* You can now undo moving zones around the canvas as well.


## Other stuff

* CICD will not print checksum of generated executable so it can be easily compared to the executable in release

