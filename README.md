# service.yamaha.monitor

Tested on Yamaha RX-681 Multicast Receiver and older RX-671 YNC (Yamaha Network Control) receiver.

2 channels or less, sets audio as 7channelStereo, sets video as Surround.  
More than 2 channels sets STRAIGHT mode.  
Additionally have option to pause video at start allowing time for screen refresh.

No AVinfo on-screen support for older YNC models.

Allows for optional video pause seconds at start to allow TV time to refresh screen. Only applicable to non streamed video files.

Optional AVinfo screen display (multicast receivers)

Optional ability to return to a mode after playback finished.

<img width="1920" height="1080" alt="screenshot00000" src="https://github.com/user-attachments/assets/18886a93-e47f-4f1b-ac0e-266995fe0eec" />

Revisions
=========

5/10/2026 - Added ability to skip pausing if video FPS is 29.97 , 30 or 60 as this does not cause some TV's to go through tiresome screen blackout and refresh.  In another words, don't pause if i don't need to.
