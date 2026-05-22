# Changelog

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

