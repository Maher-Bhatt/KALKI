using System;
using System.Threading.Tasks;
using Windows.Media.Control;

namespace MediaInfo
{
    class Program
    {
        static async Task Main(string[] args)
        {
            try
            {
                var sessionManager = await GlobalSystemMediaTransportControlsSessionManager.RequestAsync();
                var session = sessionManager.GetCurrentSession();
                
                if (args.Length > 0 && session != null)
                {
                    if (args[0] == "play") await session.TryPlayAsync();
                    else if (args[0] == "pause") await session.TryPauseAsync();
                    else if (args[0] == "next") await session.TrySkipNextAsync();
                    else if (args[0] == "prev") await session.TrySkipPreviousAsync();
                    else if (args[0] == "toggle") await session.TryTogglePlayPauseAsync();
                    return;
                }

                if (session == null)
                {
                    Console.WriteLine("{\"status\": \"NoMedia\"}");
                    return;
                }

                var mediaProperties = await session.TryGetMediaPropertiesAsync();
                var playbackInfo = session.GetPlaybackInfo();
                
                string title = mediaProperties.Title?.Replace("\"", "\\\"") ?? "";
                string artist = mediaProperties.Artist?.Replace("\"", "\\\"") ?? "";
                string album = mediaProperties.AlbumTitle?.Replace("\"", "\\\"") ?? "";
                string status = playbackInfo.PlaybackStatus.ToString();
                string app = session.SourceAppUserModelId ?? "";
                
                Console.WriteLine(string.Format("{{\"status\": \"{0}\", \"title\": \"{1}\", \"artist\": \"{2}\", \"album\": \"{3}\", \"app\": \"{4}\"}}", status, title, artist, album, app));
            }
            catch (Exception ex)
            {
                Console.WriteLine(string.Format("{{\"status\": \"Error\", \"message\": \"{0}\"}}", ex.Message));
            }
        }
    }
}
