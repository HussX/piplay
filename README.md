DISCLAIMERS!

1) This was designed as a working replacement for displaycams and omxplayer for PI4 and up on Bookworm LITE.  It 
   most likely won't work if you have a desktop GUI since I'm piping out to framebuffer.
2) While tested on a PI3B with multiple streams, I don't really recommend it unless you're only viewing 1 or 2.
   I WISH it were as effecient as omxplayer but it does work fairly smoothly with several streams on a 4.
3) This was tested with limited cameras.  It was strictly opencv before I tried it with some Wyze cams and
   had to have some fallbacks.  Since the mod, it seems to work with what I've tested so far.
   (Some generic Hik, Geo, Unifi, Wyze via Bridge Docker)
4) This was a joint coding effort between myself and AI.  It's been tweaked and refined 80x over to a point it runs
   fairly effeciently and has so far worked in my use cases.  It's open for improvement.  I'm sure there are things
   that could be better handled and cases that it won't work.  But it's a good starting point for someone who
   needs it!
5) This downsamples rtsp frames to 640x480 before drawing in PyQT.  That worked out FAR better than direct downsampling
   to random panel sizes in my tests.  Obviously it would look rough on a single camera screen and should be changed.
6) I need to get the apt requirements straight.  I was tracking these as testing and probably inadvertently added/missed
   some along the way.  Will test from a fresh image soon and update these.

INSTALLATION!

Modify piplay.py to your desires.  This isn't a custom screen location setup.  It's not built for multiple screens.
If you make a 2x2 grid, make sure you have 4 cameras.  I haven't tested with 3/4 but it probably works right.

Rotation turns the output to frame buffer so you don't have to fight with screen rotations on the PI itself.

FPS is self explanatory.  Lower this to skip more incoming frames and put less load on your CPU.

Grid is set up by row and column variables.  2 rows and 3 columns will be exactly that on 0 or 180 rotation.  
If you select 2x3 and rotate to 90 or 270 degrees, it'll be a 3x2.  The order of your streams will fill the grid
as though it's at 0 degrees rotation, so keep that in mind when you populate the URLs.

Once you've modified piplay.py, sudo chmod +x ./install.sh and sudo run the install.sh.  It will download the necessary python packages from apt,
move piplay.py and startup.sh to /opt/piplay, and copy over and enable the piplay.service file.  You can then
sudo systemctl start piplay per usual. (At least it should if the installer is right.)

IF YOU DIRECT DOWNLOAD PIPLAY.PY AND DO THE INSTALL YOUR OWN WAY, MAKE SURE TO PULL THE FRAMEBUFFER EXPORTS FROM STARTUP.SH!


OTHERS!

I did not come up with a plan to actively maintain this, but I'm open to recommended changes.  Or you can fork it
and modify to your heart's content.  As previously mentioned, I needed this to replace displaycams in order to 
get OSes up to date and run newer PIs.  And so long as I searched, I couldn't find anything else developed that
actually worked.  I'm just sharing the wealth.
