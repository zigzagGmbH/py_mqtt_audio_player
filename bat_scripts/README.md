# README

## Instructions for "How to autostart assigned audio players?"

> First remember to edit the PATHs in the .bat files based on where the audio player project is placed as well consider any config file related edits and number of player (and naming), prior to following the below steps

> The Steps below are general manual steps and should be followed as guidelines for future, if any edits were carried out (aforementioned). ** Currently they have been configured for CoDE


### Copy the bat files to 'home'

> Powershell commands 

```ps
cd bat_scripts
cp *.bat C:\Users\User\
# Note: After 'C:\Users\' your computer's user dir may be different (This is for CoDE as setup by Mark). So for example, for EDU, it was 'C:\Users\EDU1'

cd C:\Users\User\
ls

# You should see (among other things ...):
-a----        06.10.2025     09:25           1580 start-music-player-1.bat
-a----        06.10.2025     09:25           1580 start-music-player-2.bat
-a----        06.10.2025     09:25           1577 start-sfx-player-1.bat
-a----        06.10.2025     09:25           1578 start-sfx-player-2.bat
-a----        06.10.2025     09:25           1583 start-sys-sound-player-1.bat
-a----        06.10.2025     09:25           1583 start-sys-sound-player-2.bat
-a----        06.10.2025     09:25           1579 start-voice-player-1.bat
-a----        06.10.2025     09:25           1579 start-voice-player-2.bat
-a----        26.09.2025     11:42           1536 start_shaker_player.bat
```

### Add bat files to auto-start folder 

```ps
cd C:\Users\User\

Copy-Item -Path "C:\Users\User\start_shaker_player.bat" -Destination "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"

Copy-Item -Path "C:\Users\User\start-music-player-1.bat" -Destination "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
Copy-Item -Path "C:\Users\User\start-music-player-2.bat" -Destination "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"

Copy-Item -Path "C:\Users\User\start-sfx-player-1.bat" -Destination "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
Copy-Item -Path "C:\Users\User\start-sfx-player-2.bat" -Destination "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"

Copy-Item -Path "C:\Users\User\start-voice-player-1.bat" -Destination "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
Copy-Item -Path "C:\Users\User\start-voice-player-2.bat" -Destination "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"

Copy-Item -Path "C:\Users\User\start-sys-sound-player-1.bat" -Destination "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
Copy-Item -Path "C:\Users\User\start-sys-sound-player-2.bat" -Destination "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"


# Check:
ls "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
```

## if you need to remove ...

```ps
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\*.bat" | Remove-Item -Confirm
```