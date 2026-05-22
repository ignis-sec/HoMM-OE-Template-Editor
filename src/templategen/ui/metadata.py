
VERSION = "v0.0.6"
CHANGELOG = """
<h1 id="changelog">Changelog</h1>
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