Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asyncOp = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType = WindowsRuntime]::RequestAsync()
$task = [System.WindowsRuntimeSystemExtensions]::AsTask($asyncOp)
$sessionManager = $task.Result
$session = $sessionManager.GetCurrentSession()
if ($session) {
    $mediaOp = $session.TryGetMediaPropertiesAsync()
    $mediaTask = [System.WindowsRuntimeSystemExtensions]::AsTask($mediaOp)
    $mediaProperties = $mediaTask.Result
    $playbackInfo = $session.GetPlaybackInfo()
    $status = $playbackInfo.PlaybackStatus
    $title = $mediaProperties.Title
    $artist = $mediaProperties.Artist
    $album = $mediaProperties.AlbumTitle
    Write-Output "{""status"": ""$status"", ""title"": ""$title"", ""artist"": ""$artist"", ""album"": ""$album""}"
} else {
    Write-Output "{""status"": ""NoMedia""}"
}
