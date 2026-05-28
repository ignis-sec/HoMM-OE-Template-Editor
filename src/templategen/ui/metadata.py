
VERSION = "v0.1.1"
CHANGELOG = """
<h1 id="changelog">Changelog</h1>
<h1 id="v0-1-1">v0.1.1</h1>
<h2 id="new-features">New Features</h2>
<ul>
<li>Added an option to rebuild road layout from current zone layout (graph view only)</li>
</ul>
<h2 id="bugfixes">Bugfixes</h2>
<ul>
<li><p>Crossroads are now displayed correctly in the road editor.</p>
</li>
<li><p>Fix difficulty navigating via zoom in/out on larger template graphs.</p>
</li>
</ul>
<hr>
<h1 id="v0-1-0-significant-changes">v0.1.0 - Significant Changes</h1>
<h2 id="new-features">New Features</h2>
<ul>
<li><p>On first run, you&#39;ll be asked to enter the game install directory, and the editor will mine the game data as well as required thumbnail images to be used in the editor. You can chose not to, but you will lose the ability to use the catalog explorer, see icons for objects, spells and artifacts, and you will not have sid&#39;s fill dropdowns in editor fields.</p>
</li>
<li><p>All dropdowns now have names and thumbnails of list items for a better user experience.</p>
</li>
<li><p>Editor fields now correctly narrow down which sid types are allowed in which field instead of containing a list of everything in the game.</p>
</li>
<li><p>Properly implemented bonus selection in template settings.</p>
</li>
<li><p>Catalog explorer now shows detailed content about artifacts, spells, resources and map objects.</p>
</li>
<li><p>Added road view mode / road editor, which makes managing road connections much easier.</p>
</li>
<li><p>Added a logging window to troubleshoot issues.</p>
</li>
<li><p>Object/resource variants are now included in the catalog explorer.</p>
</li>
</ul>
<h2 id="improvements">Improvements</h2>
<ul>
<li><p>Faction selection fields are now proper dropdowns instead of free fields.</p>
</li>
<li><p>Road and Biome selection are now type-aware and will correctly display relevant options in the dropdowns based on which type was selected.</p>
</li>
<li><p>Changed the layout split direction for catalog explorer so its easier to use (list on left, details on right instead of top/bottom split)</p>
</li>
<li><p>Improved UX for content items elements on mandatory content lists and content limits.</p>
</li>
<li><p>Improved UI load times.</p>
</li>
<li><p>Validation checks will now perform a sanity check for road connections and warn about possible disconnections.</p>
</li>
<li><p>Content lists can now be renamed.</p>
</li>
</ul>
<h2 id="bugfixes">Bugfixes</h2>
<ul>
<li><p>Removed empty type option from road types.</p>
</li>
<li><p>Value overrides tab on template editor is now scrollable and won&#39;t cause super long dialog windows that overflow the screen if there are too many overrides.</p>
</li>
<li><p>Default owner player and object variant is now correctly set as (none) instead of Player1/variant 0.</p>
</li>
<li><p>Templates with disconnected graphs (tournament ones such as exodus or sprint) will now be autopositioned in a way that doesn&#39;t overlap them.</p>
</li>
</ul>
<hr>
<h1 id="v0-0-7">v0.0.7</h1>
<h2 id="new-features">New Features</h2>
<ul>
<li><p>Windows executable is now released as a zip file that also contains catalog.json and images.</p>
</li>
<li><p>Save zone positions in the editor canvas to the thumbnail exif so next time it is opened we can restore the same positions in editor (without adding junk to the template file)</p>
</li>
</ul>
<h2 id="bugfixes">Bugfixes</h2>
<ul>
<li>Fixed catalog explorer and related autofills not working on windows executable.</li>
</ul>
<h1 id="v0-0-6">v0.0.6</h1>
<h2 id="new-features">New features</h2>
<ul>
<li>Added a context menu on the zone layout canvas that has various options for aligning selected zones:<ul>
<li>Align Horizontally</li>
<li>Align Vertically</li>
<li>Align in a Line</li>
<li>Align in a Circle</li>
<li>Set Equal Distance</li>
<li>Set Equal Distance (X)</li>
<li>Set Equal Distance (Y)</li>
</ul>
</li>
<li><p>Item and spell data now included in the catalog viewer.</p>
</li>
<li><p>Added items and spells to the catalog explorer.</p>
</li>
<li><p>You can now add multiple connections between same two zones.</p>
</li>
<li><p>Connection type between zones can now be changed in the inspector widget.</p>
</li>
<li><p>Added changelog to the &quot;about&quot; window.</p>
</li>
</ul>
<h2 id="bugfixes">Bugfixes</h2>
<ul>
<li><p>Fixed a bug that caused connections to be retained in template files and thumbnail images when a zone that has connections was deleted.</p>
</li>
<li><p>Fixed a bug that caused zone richness colors (empty, blue, golden) in the thumbnail to be incorrectly set when zones had equal values.</p>
<ul>
<li>The way colors were set was they were sorted by value then split 30/40/30 and assigned colors. The correct way was to set threshold between max/min zone values and color according to that so zones with equal values did not get assigned to different buckets.</li>
</ul>
</li>
<li><p>In template -&gt; template settings -&gt; global bans, item and spell id&#39;s are now correctly listed (instead of listing every SID in catalog)</p>
</li>
<li><p>Fixed a problem with roads widget in a zone going invisible.</p>
</li>
<li><p>Fixed dropdowns and initial values when creating a road, now you can select a connection name from dropdown.</p>
</li>
<li><p>You can now undo moving zones around the canvas as well.</p>
</li>
</ul>
<h2 id="other-stuff">Other stuff</h2>
<ul>
<li>CICD will not print checksum of generated executable so it can be easily compared to the executable in release</li>
</ul>

"""