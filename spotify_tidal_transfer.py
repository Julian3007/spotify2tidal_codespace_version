#!/usr/bin/env python3
"""
Spotify to TIDAL Transfer Tool - Cloud Optimized Version
A clean, unified solution for transferring music data between Spotify and TIDAL

Features:
- Cloud-friendly direct transfer (no CSV intermediates)
- Interactive credential setup  
- Enhanced search with confidence scoring
- Real-time progress tracking
- Transfer statistics
- Failed items tracking and reporting

Author: Generated for Julian Meyer
Date: October 16, 2025
"""

import os
import sys
import json
import csv
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Third-party imports
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    import tidalapi
    from tqdm import tqdm
except ImportError as e:
    print(f"❌ Missing required package: {e}")
    print("📦 Please install with: pip install spotipy tidalapi tqdm pandas")
    sys.exit(1)


class SpotifyTidalTransfer:

    def __init__(self):
        self.spotify = None
        self.tidal = None
        self.output_dir = Path("exports")
        self.output_dir.mkdir(exist_ok=True)
        self.transfer_stats = {
            'songs_imported': 0,
            'artists_imported': 0, 
            'albums_imported': 0,
            'playlists_created': 0,
            'total_failed': 0
        }
        # Store failed items for detailed reporting
        self.failed_items = {
            'songs': [],
            'artists': [],
            'albums': [],
            'playlist_tracks': []
        }

    def is_cloud_environment(self):
        """Detect if running in cloud environment (Codespaces, Replit, etc.)"""
        return (os.getenv('CODESPACES') is not None or 
                os.getenv('REPL_ID') is not None or 
                os.getenv('GITPOD_WORKSPACE_ID') is not None)

    def setup_credentials_interactive(self):
        """Interactive credential setup for cloud environments"""
        print("\n🔑 CREDENTIAL SETUP")
        print("=" * 30)
        print("You need Spotify API credentials from: https://developer.spotify.com/")
        print("1. Go to Spotify Developer Dashboard")
        print("2. Create an app (any name)")
        print("3. Copy Client ID and Client Secret")
        print("4. Add redirect URI: https://example.com/callback")
        print("")
        
        client_id = input("Enter Spotify Client ID: ").strip()
        if not client_id:
            print("❌ Client ID required")
            return False
            
        client_secret = input("Enter Spotify Client Secret: ").strip()
        if not client_secret:
            print("❌ Client Secret required")
            return False
        
        # Set for this session
        os.environ['SPOTIFY_CLIENT_ID'] = client_id
        os.environ['SPOTIFY_CLIENT_SECRET'] = client_secret
        os.environ['SPOTIFY_REDIRECT_URI'] = "https://example.com/callback"
        
        print("✅ Credentials set for this session")
        return True

    def connect_spotify(self):
        """Connect to Spotify and set self.spotify. Returns True if successful."""
        try:
            client_id = os.getenv("SPOTIFY_CLIENT_ID")
            client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
            redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
            
            def _mask(val: Optional[str]) -> str:
                if not val:
                    return "(missing)"
                v = str(val)
                if len(v) <= 4:
                    return "****"
                return "*" * (len(v) - 4) + v[-4:]

            if not client_id or not client_secret:
                print("❌ Spotify credentials not set. Please setup credentials first (option 1)")
                print(f"🔎 SPOTIFY_CLIENT_ID present: {bool(client_id)} (masked: {_mask(client_id)})")
                print(f"🔎 SPOTIFY_REDIRECT_URI: {redirect_uri!r}")
                return False
            
            print(f"🔎 SPOTIFY_CLIENT_ID present: {bool(client_id)} (masked: {_mask(client_id)})")
            print(f"🔎 SPOTIFY_REDIRECT_URI: {redirect_uri!r}")
            scope = "user-library-read playlist-read-private user-follow-read"
            auth_manager = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope)
            
            try:
                self.spotify = spotipy.Spotify(auth_manager=auth_manager)
                user = self.spotify.current_user()
                print(f"✅ Connected to Spotify as {user.get('display_name', user['id'])}")
                return True
            except Exception:
                try:
                    import webbrowser
                    print("🔁 Falling back to manual OAuth flow. A browser window will open; after you authorize, paste the full redirect URL here.")
                    auth_url = auth_manager.get_authorize_url()
                    print(f"🔗 Authorization URL: {auth_url}")
                    try:
                        webbrowser.open(auth_url)
                    except Exception:
                        pass

                    code = None
                    for attempt in range(3):
                        redirect_response = input("Paste the full redirect URL after authorizing (the URL in your browser address bar): ").strip()
                        try:
                            code = auth_manager.parse_response_code(redirect_response)
                        except Exception:
                            code = None
                        
                        if not code:
                            try:
                                from urllib.parse import urlparse, parse_qs
                                parsed = urlparse(redirect_response)
                                qs = parse_qs(parsed.query)
                                if 'code' in qs:
                                    code = qs['code'][0]
                            except Exception:
                                code = None

                        if not code:
                            print("⚠️ It looks like the pasted URL does not contain an authorization code. Make sure you paste the final redirect URL (it should contain 'code=').")
                            if attempt < 2:
                                print("Please try again.")
                                continue
                            else:
                                print("Aborting manual OAuth after 3 failed attempts.")
                                raise Exception("No authorization code provided by user")
                        else:
                            break

                    token_info = auth_manager.get_access_token(code)
                    access_token = token_info['access_token'] if isinstance(token_info, dict) and 'access_token' in token_info else token_info
                    if not access_token:
                        print("❌ Could not obtain access token from the provided response.")
                        return False
                    self.spotify = spotipy.Spotify(auth=access_token)
                    user = self.spotify.current_user()
                    print(f"✅ Connected to Spotify as {user.get('display_name', user['id'])}")
                    return True
                except Exception as exc:
                    print(f"❌ Manual OAuth flow failed: {exc}")
                    self.spotify = None
                    return False
            return True
        except Exception as e:
            msg = str(e)
            print(f"❌ Failed to connect to Spotify: {msg}")
            if 'invalid_client' in msg.lower() or 'invalid client' in msg.lower():
                print("   ℹ️ Common causes: redirect URI mismatch in Spotify Dashboard, incorrect client id/secret, or using the wrong app.")
            self.spotify = None
            return False

    def connect_tidal(self):
        """Connect to TIDAL and set self.tidal. Returns True if successful."""
        try:
            import tidalapi as _tidal
            version = getattr(_tidal, '__version__', 'unknown')
            print(f"🔎 tidalapi version: {version}")
            session = _tidal.Session()
            print("🔑 Initiating TIDAL login (device OAuth)...")
            try:
                session.login_oauth_simple()
            except Exception as inner_e:
                msg = str(inner_e)
                if 'invalid_client' in msg.lower():
                    print("❌ TIDAL authentication reported invalid_client.")
                    print("   Possible causes:")
                    print("   1. Outdated tidalapi library (try: pip install --upgrade tidalapi)")
                    print("   2. TIDAL changed public client credentials used by tidalapi (update library)")
                    print("   3. Regional restrictions or account type not supported")
                    print("   4. Temporary TIDAL auth service issue")
                    print("   Next steps:")
                    print("     a) Upgrade: pip install --upgrade tidalapi")
                    print("     b) If still failing, file an issue at https://github.com/tidalapi/tidalapi with the error.")
                raise
            self.tidal = session
            username = getattr(getattr(self.tidal, 'user', None), 'username', None)
            print(f"✅ Connected to TIDAL as {username or 'Unknown'}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to TIDAL: {e}")
            self.tidal = None
            return False

    def test_connections(self):
        """Test connections to both services"""
        print("\n🧪 Testing Connections")
        print("-" * 30)
        
        spotify_ok = self.connect_spotify()
        tidal_ok = self.connect_tidal()
        
        print(f"\n📊 Status: Spotify {'✅' if spotify_ok else '❌'} | TIDAL {'✅' if tidal_ok else '❌'}")
        return spotify_ok, tidal_ok

    def _normalize_search_text(self, text: str) -> str:
        """Normalize text for better search matching."""
        import re
        if not text:
            return ""
        
        # Remove content in parentheses/brackets (feat., live, remaster, etc.)
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        
        # Remove common noise words
        noise_words = ['feat.', 'ft.', 'featuring', 'with', 'vs.', 'vs', '&']
        for word in noise_words:
            text = re.sub(r'\b' + re.escape(word) + r'\b', '', text, flags=re.IGNORECASE)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        return text.strip()
    
    def _extract_primary_artist(self, artist_str: str) -> str:
        """Extract the primary (first) artist from a string that may contain multiple artists."""
        if not artist_str:
            return ""
        
        # Split on common separators
        for sep in [',', ';', '&', ' and ', ' x ', ' X ']:
            if sep in artist_str:
                return artist_str.split(sep)[0].strip()
        
        return artist_str.strip()
    
    def _calculate_artist_similarity(self, artist1: str, artist2: str) -> float:
        """Calculate simple similarity score between two artist names (0.0 to 1.0)."""
        if not artist1 or not artist2:
            return 0.0
        
        a1 = artist1.lower().strip()
        a2 = artist2.lower().strip()
        
        # Exact match
        if a1 == a2:
            return 1.0
        
        # One contains the other
        if a1 in a2 or a2 in a1:
            return 0.9
        
        # Check if primary artist matches (useful for "Artist feat. Other")
        primary1 = self._extract_primary_artist(a1)
        primary2 = self._extract_primary_artist(a2)
        if primary1 == primary2:
            return 0.85
        
        # Simple word overlap
        words1 = set(a1.split())
        words2 = set(a2.split())
        if words1 and words2:
            overlap = len(words1 & words2) / max(len(words1), len(words2))
            return overlap * 0.7
        
        return 0.0
    
    def search_tidal_track(self, track_name: str, artist_name: str, album_name: str = None, duration_ms: int = None) -> Optional[Dict]:
        """
        Search for a track on TIDAL using progressive fallback queries and smart result filtering.
        Returns the best match as a dict with 'track', 'confidence', and 'query_used' keys, or None if not found.
        """
        import time
        
        # Normalize inputs
        track_clean = self._normalize_search_text(track_name)
        artist_clean = self._normalize_search_text(artist_name)
        primary_artist = self._extract_primary_artist(artist_clean)
        
        if not track_clean:
            return None
        
        # Progressive fallback queries (from most specific to least specific)
        queries = [
            f'"{track_clean}" "{primary_artist}"' if primary_artist else None,
            f'{track_clean} {primary_artist}' if primary_artist else None,
            f'{track_clean} {artist_clean}' if artist_clean and artist_clean != primary_artist else None,
            track_clean
        ]
        queries = [q for q in queries if q]  # Remove None entries
        
        best_match = None
        best_score = 0.0
        query_used = None
        
        for query in queries:
            try:
                search_result = self.tidal.search(query, limit=10)
                tracks = search_result.get('tracks', [])
                
                if not tracks:
                    continue
                
                # Score each result
                for track in tracks:
                    score = 0.0
                    
                    # Artist similarity (most important)
                    track_artist = track.artist.name if hasattr(track, 'artist') and track.artist else ""
                    artist_sim = self._calculate_artist_similarity(artist_name, track_artist)
                    score += artist_sim * 0.6
                    
                    # Album match (if available)
                    if album_name and hasattr(track, 'album') and track.album:
                        album_sim = self._calculate_artist_similarity(album_name, track.album.name)
                        score += album_sim * 0.2
                    
                    # Duration match (if available)
                    if duration_ms and hasattr(track, 'duration') and track.duration:
                        duration_diff = abs(duration_ms - track.duration * 1000)
                        if duration_diff < 5000:  # Within 5 seconds
                            score += 0.2
                        elif duration_diff < 15000:  # Within 15 seconds
                            score += 0.1
                    else:
                        score += 0.1  # Small bonus if no duration to compare
                    
                    # Track name similarity (basic check)
                    track_name_clean = self._normalize_search_text(track.name if hasattr(track, 'name') else "")
                    if track_clean.lower() in track_name_clean.lower() or track_name_clean.lower() in track_clean.lower():
                        score += 0.1
                    
                    # Update best match
                    if score > best_score:
                        best_score = score
                        best_match = track
                        query_used = query
                
                # If we found a high-confidence match, stop searching
                if best_score >= 0.8:
                    break
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"    ⚠️ Search error for query '{query}': {e}")
                continue
        
        # Only return matches with reasonable confidence
        if best_match and best_score >= 0.5:
            return {
                'track': best_match,
                'confidence': best_score,
                'query_used': query_used
            }
        
        return None

    def save_failed_items_report(self, category: str = "all"):
        """Save detailed report of failed items to a text file"""
        if not any(self.failed_items.values()):
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"failed_items_{category}_{timestamp}.txt"
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"🚫 FAILED ITEMS REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")
                
                if category == "all" or category == "songs":
                    if self.failed_items['songs']:
                        f.write(f"🎵 FAILED SONGS ({len(self.failed_items['songs'])}):\n")
                        f.write("-" * 40 + "\n")
                        for item in self.failed_items['songs']:
                            f.write(f"• {item['name']} - {item['artist']}\n")
                            if item.get('album'):
                                f.write(f"  Album: {item['album']}\n")
                            if item.get('reason'):
                                f.write(f"  Reason: {item['reason']}\n")
                            f.write("\n")
                        f.write("\n")
                
                if category == "all" or category == "artists":
                    if self.failed_items['artists']:
                        f.write(f"👨‍🎤 FAILED ARTISTS ({len(self.failed_items['artists'])}):\n")
                        f.write("-" * 40 + "\n")
                        for item in self.failed_items['artists']:
                            f.write(f"• {item['name']}\n")
                            if item.get('reason'):
                                f.write(f"  Reason: {item['reason']}\n")
                            f.write("\n")
                        f.write("\n")
                
                if category == "all" or category == "albums":
                    if self.failed_items['albums']:
                        f.write(f"💿 FAILED ALBUMS ({len(self.failed_items['albums'])}):\n")
                        f.write("-" * 40 + "\n")
                        for item in self.failed_items['albums']:
                            f.write(f"• {item['name']} - {item['artist']}\n")
                            if item.get('reason'):
                                f.write(f"  Reason: {item['reason']}\n")
                            f.write("\n")
                        f.write("\n")
                
                if category == "all" or category == "playlist_tracks":
                    if self.failed_items['playlist_tracks']:
                        f.write(f"📋 FAILED PLAYLIST TRACKS ({len(self.failed_items['playlist_tracks'])}):\n")
                        f.write("-" * 40 + "\n")
                        current_playlist = None
                        for item in self.failed_items['playlist_tracks']:
                            if item['playlist'] != current_playlist:
                                current_playlist = item['playlist']
                                f.write(f"\n📂 Playlist: {current_playlist}\n")
                            f.write(f"  • {item['name']} - {item['artist']}\n")
                            if item.get('reason'):
                                f.write(f"    Reason: {item['reason']}\n")
                        f.write("\n")
                
                f.write("=" * 70 + "\n")
                f.write("💡 TIP: You can manually search for these items in TIDAL\n")
                f.write("🔍 Some tracks might be available under different names or artists\n")
            
            print(f"📝 Failed items report saved: {filename}")
            return filepath
            
        except Exception as e:
            print(f"⚠️ Could not save failed items report: {e}")
            return None

    def print_failed_items_summary(self, category: str = "all"):
        """Print a summary of failed items to console"""
        total_failed = sum(len(items) for items in self.failed_items.values())
        
        if total_failed == 0:
            print("✅ No failed items to report!")
            return
        
        print(f"\n🚫 FAILED ITEMS SUMMARY")
        print("=" * 30)
        
        if category == "all" or category == "songs":
            if self.failed_items['songs']:
                print(f"🎵 Songs: {len(self.failed_items['songs'])}")
                for item in self.failed_items['songs'][:5]:  # Show first 5
                    print(f"  • {item['name']} - {item['artist']}")
                if len(self.failed_items['songs']) > 5:
                    print(f"  ... and {len(self.failed_items['songs']) - 5} more")
        
        if category == "all" or category == "artists":
            if self.failed_items['artists']:
                print(f"👨‍🎤 Artists: {len(self.failed_items['artists'])}")
                for item in self.failed_items['artists'][:3]:  # Show first 3
                    print(f"  • {item['name']}")
                if len(self.failed_items['artists']) > 3:
                    print(f"  ... and {len(self.failed_items['artists']) - 3} more")
        
        if category == "all" or category == "albums":
            if self.failed_items['albums']:
                print(f"💿 Albums: {len(self.failed_items['albums'])}")
                for item in self.failed_items['albums'][:3]:  # Show first 3
                    print(f"  • {item['name']} - {item['artist']}")
                if len(self.failed_items['albums']) > 3:
                    print(f"  ... and {len(self.failed_items['albums']) - 3} more")
        
        if category == "all" or category == "playlist_tracks":
            if self.failed_items['playlist_tracks']:
                print(f"📋 Playlist tracks: {len(self.failed_items['playlist_tracks'])}")
                playlists = set(item['playlist'] for item in self.failed_items['playlist_tracks'])
                print(f"  Across {len(playlists)} playlists")
        
        print("\n💡 Full details will be saved to a report file")

    def direct_transfer_songs(self):
        """Transfer liked songs directly to TIDAL favorites"""
        print("\n🎵 TRANSFERRING LIKED SONGS")
        print("=" * 35)
        
        if not self.spotify or not self.tidal:
            print("❌ Both services must be connected first")
            return
        
        try:
            imported = 0
            failed = 0
            
            print("📥 Fetching your liked songs from Spotify...")
            offset = 0
            limit = 50
            
            while True:
                results = self.spotify.current_user_saved_tracks(limit=limit, offset=offset)
                items = results['items']
                
                if not items:
                    break
                
                print(f"🔄 Processing batch {offset//limit + 1} ({len(items)} songs)...")
                
                for item in items:
                    track = item['track']
                    if track and track['type'] == 'track':
                        try:
                            match_result = self.search_tidal_track(
                                track_name=track['name'],
                                artist_name=', '.join([artist['name'] for artist in track['artists']]),
                                album_name=track['album']['name'],
                                duration_ms=track['duration_ms']
                            )
                            
                            if match_result:
                                self.tidal.user.favorites.add_track(match_result['track'].id)
                                imported += 1
                                confidence_emoji = "✅" if match_result['confidence'] >= 0.8 else "⚠️"
                                print(f"  {confidence_emoji} {track['name']} - {track['artists'][0]['name']} ({match_result['confidence']:.0%})")
                            else:
                                failed += 1
                                # Store failed song details
                                self.failed_items['songs'].append({
                                    'name': track['name'],
                                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                                    'album': track['album']['name'],
                                    'reason': 'No match found on TIDAL'
                                })
                                print(f"  ❌ {track['name']} - {track['artists'][0]['name']}")
                        except Exception as e:
                            failed += 1
                            # Store failed song details
                            self.failed_items['songs'].append({
                                'name': track['name'],
                                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                                'album': track['album']['name'],
                                'reason': f'Error: {str(e)}'
                            })
                            print(f"  ❌ Error: {track['name']} - {e}")
                
                offset += limit
                if len(items) < limit:
                    break
            
            self.transfer_stats['songs_imported'] += imported
            self.transfer_stats['total_failed'] += failed
            
            print(f"\n📊 SONGS TRANSFER COMPLETE")
            print(f"✅ Successfully imported: {imported}")
            print(f"❌ Failed: {failed}")
            if imported + failed > 0:
                success_rate = (imported / (imported + failed)) * 100
                print(f"📈 Success rate: {success_rate:.1f}%")
            
            # Show failed items summary and save report
            if failed > 0:
                self.print_failed_items_summary("songs")
                self.save_failed_items_report("songs")
                
        except Exception as e:
            print(f"❌ Error during songs transfer: {e}")

    def direct_transfer_artists(self):
        """Transfer followed artists directly to TIDAL favorites"""
        print("\n👨‍🎤 TRANSFERRING FOLLOWED ARTISTS")
        print("=" * 40)
        
        if not self.spotify or not self.tidal:
            print("❌ Both services must be connected first")
            return
        
        try:
            imported = 0
            failed = 0
            
            print("📥 Fetching your followed artists from Spotify...")
            after = None
            
            while True:
                results = self.spotify.current_user_followed_artists(limit=50, after=after)
                artists = results['artists']['items']
                
                if not artists:
                    break
                
                print(f"🔄 Processing {len(artists)} artists...")
                
                for artist in artists:
                    try:
                        search_result = self.tidal.search(artist['name'], limit=5)
                        tidal_artists = search_result.get('artists', [])
                        
                        if tidal_artists:
                            # Find best match
                            best_match = None
                            best_score = 0
                            
                            for tidal_artist in tidal_artists:
                                score = self._calculate_artist_similarity(artist['name'], tidal_artist.name)
                                if score > best_score:
                                    best_score = score
                                    best_match = tidal_artist
                            
                            if best_match and best_score >= 0.7:
                                self.tidal.user.favorites.add_artist(best_match.id)
                                imported += 1
                                confidence_emoji = "✅" if best_score >= 0.9 else "⚠️"
                                print(f"  {confidence_emoji} {artist['name']} ({best_score:.0%})")
                            else:
                                failed += 1
                                # Store failed artist details
                                self.failed_items['artists'].append({
                                    'name': artist['name'],
                                    'reason': f'No good match found (best score: {best_score:.0%})' if best_match else 'No match found on TIDAL'
                                })
                                print(f"  ❌ {artist['name']} (no good match)")
                        else:
                            failed += 1
                            # Store failed artist details
                            self.failed_items['artists'].append({
                                'name': artist['name'],
                                'reason': 'Not found on TIDAL'
                            })
                            print(f"  ❌ {artist['name']} (not found)")
                    except Exception as e:
                        failed += 1
                        # Store failed artist details
                        self.failed_items['artists'].append({
                            'name': artist['name'],
                            'reason': f'Error: {str(e)}'
                        })
                        print(f"  ❌ Error: {artist['name']} - {e}")
                
                if len(artists) < 50:
                    break
                after = artists[-1]['id']
            
            self.transfer_stats['artists_imported'] += imported
            self.transfer_stats['total_failed'] += failed
            
            print(f"\n📊 ARTISTS TRANSFER COMPLETE")
            print(f"✅ Successfully imported: {imported}")
            print(f"❌ Failed: {failed}")
            if imported + failed > 0:
                success_rate = (imported / (imported + failed)) * 100
                print(f"📈 Success rate: {success_rate:.1f}%")
            
            # Show failed items summary and save report
            if failed > 0:
                self.print_failed_items_summary("artists")
                self.save_failed_items_report("artists")
                
        except Exception as e:
            print(f"❌ Error during artists transfer: {e}")

    def direct_transfer_albums(self):
        """Transfer saved albums directly to TIDAL favorites"""
        print("\n💿 TRANSFERRING SAVED ALBUMS")
        print("=" * 35)
        
        if not self.spotify or not self.tidal:
            print("❌ Both services must be connected first")
            return
        
        try:
            imported = 0
            failed = 0
            
            print("📥 Fetching your saved albums from Spotify...")
            offset = 0
            limit = 50
            
            while True:
                results = self.spotify.current_user_saved_albums(limit=limit, offset=offset)
                items = results['items']
                
                if not items:
                    break
                
                print(f"🔄 Processing batch {offset//limit + 1} ({len(items)} albums)...")
                
                for item in items:
                    album = item['album']
                    try:
                        artist_name = ', '.join([artist['name'] for artist in album['artists']])
                        query = f"{album['name']} {artist_name}"
                        search_result = self.tidal.search(query, limit=5)
                        tidal_albums = search_result.get('albums', [])
                        
                        if tidal_albums:
                            # Find best match
                            best_match = None
                            best_score = 0
                            
                            for tidal_album in tidal_albums:
                                album_score = self._calculate_artist_similarity(album['name'], tidal_album.name)
                                artist_score = self._calculate_artist_similarity(artist_name, tidal_album.artist.name if tidal_album.artist else "")
                                combined_score = (album_score * 0.7) + (artist_score * 0.3)
                                
                                if combined_score > best_score:
                                    best_score = combined_score
                                    best_match = tidal_album
                            
                            if best_match and best_score >= 0.6:
                                self.tidal.user.favorites.add_album(best_match.id)
                                imported += 1
                                confidence_emoji = "✅" if best_score >= 0.8 else "⚠️"
                                print(f"  {confidence_emoji} {album['name']} - {artist_name} ({best_score:.0%})")
                            else:
                                failed += 1
                                # Store failed album details
                                self.failed_items['albums'].append({
                                    'name': album['name'],
                                    'artist': artist_name,
                                    'reason': f'No good match found (best score: {best_score:.0%})' if best_match else 'No match found on TIDAL'
                                })
                                print(f"  ❌ {album['name']} - {artist_name} (no good match)")
                        else:
                            failed += 1
                            # Store failed album details
                            self.failed_items['albums'].append({
                                'name': album['name'],
                                'artist': artist_name,
                                'reason': 'Not found on TIDAL'
                            })
                            print(f"  ❌ {album['name']} - {artist_name} (not found)")
                    except Exception as e:
                        failed += 1
                        # Store failed album details
                        self.failed_items['albums'].append({
                            'name': album['name'],
                            'artist': artist_name,
                            'reason': f'Error: {str(e)}'
                        })
                        print(f"  ❌ Error: {album['name']} - {e}")
                
                offset += limit
                if len(items) < limit:
                    break
            
            self.transfer_stats['albums_imported'] += imported
            self.transfer_stats['total_failed'] += failed
            
            print(f"\n📊 ALBUMS TRANSFER COMPLETE")
            print(f"✅ Successfully imported: {imported}")
            print(f"❌ Failed: {failed}")
            if imported + failed > 0:
                success_rate = (imported / (imported + failed)) * 100
                print(f"📈 Success rate: {success_rate:.1f}%")
            
            # Show failed items summary and save report
            if failed > 0:
                self.print_failed_items_summary("albums")
                self.save_failed_items_report("albums")
                
        except Exception as e:
            print(f"❌ Error during albums transfer: {e}")

    def direct_transfer_playlists(self):
        """Transfer playlists directly to TIDAL"""
        print("\n📋 TRANSFERRING PLAYLISTS")
        print("=" * 30)
        
        if not self.spotify or not self.tidal:
            print("❌ Both services must be connected first")
            return
        
        try:
            playlists_created = 0
            total_imported = 0
            total_failed = 0
            
            print("📥 Fetching your playlists from Spotify...")
            playlists = self.spotify.current_user_playlists(limit=50)
            
            print(f"Found {len(playlists['items'])} playlists")
            
            for playlist in playlists['items']:
                if playlist is None:
                    continue
                
                playlist_name = playlist['name']
                playlist_id = playlist['id']
                track_count = playlist['tracks']['total']
                
                print(f"\n📂 Processing: {playlist_name} ({track_count} tracks)")
                
                try:
                    # Create TIDAL playlist
                    user_playlists = self.tidal.user.playlists()
                    tidal_playlist = next((pl for pl in user_playlists if pl.name == playlist_name), None)
                    
                    if not tidal_playlist:
                        tidal_playlist = self.tidal.user.create_playlist(playlist_name, description="Imported from Spotify")
                        print(f"  ➕ Created TIDAL playlist: {playlist_name}")
                        playlists_created += 1
                    else:
                        print(f"  ℹ️ Using existing TIDAL playlist: {playlist_name}")
                    
                    # Get and transfer tracks
                    imported = 0
                    failed = 0
                    batch_ids = []
                    
                    offset = 0
                    while True:
                        tracks = self.spotify.playlist_tracks(playlist_id, limit=100, offset=offset)
                        
                        for item in tracks['items']:
                            track = item.get('track')
                            if track and track.get('type') == 'track':
                                try:
                                    match_result = self.search_tidal_track(
                                        track_name=track['name'],
                                        artist_name=', '.join([artist['name'] for artist in track['artists']]),
                                        album_name=track['album']['name'],
                                        duration_ms=track['duration_ms']
                                    )
                                    
                                    if match_result:
                                        batch_ids.append(match_result['track'].id)
                                        imported += 1
                                        confidence_emoji = "✅" if match_result['confidence'] >= 0.8 else "⚠️"
                                        print(f"    {confidence_emoji} {track['name']} - {track['artists'][0]['name']} ({match_result['confidence']:.0%})")
                                        
                                        if len(batch_ids) == 50:
                                            tidal_playlist.add(batch_ids)
                                            batch_ids = []
                                    else:
                                        failed += 1
                                        # Store failed playlist track details
                                        self.failed_items['playlist_tracks'].append({
                                            'name': track['name'],
                                            'artist': ', '.join([artist['name'] for artist in track['artists']]),
                                            'album': track['album']['name'],
                                            'playlist': playlist_name,
                                            'reason': 'No match found on TIDAL'
                                        })
                                        print(f"    ❌ {track['name']} - {track['artists'][0]['name']}")
                                except Exception as e:
                                    failed += 1
                                    # Store failed playlist track details
                                    self.failed_items['playlist_tracks'].append({
                                        'name': track['name'],
                                        'artist': ', '.join([artist['name'] for artist in track['artists']]),
                                        'album': track['album']['name'],
                                        'playlist': playlist_name,
                                        'reason': f'Error: {str(e)}'
                                    })
                                    print(f"    ❌ Error: {track['name']} - {e}")
                        
                        if not tracks['next']:
                            break
                        offset += 100
                    
                    # Add remaining tracks
                    if batch_ids:
                        tidal_playlist.add(batch_ids)
                    
                    total_imported += imported
                    total_failed += failed
                    
                    print(f"  📊 Playlist complete: {imported} imported, {failed} failed")
                    
                except Exception as e:
                    print(f"  ❌ Error processing playlist '{playlist_name}': {e}")
            
            self.transfer_stats['playlists_created'] += playlists_created
            self.transfer_stats['songs_imported'] += total_imported
            self.transfer_stats['total_failed'] += total_failed
            
            print(f"\n📊 PLAYLISTS TRANSFER COMPLETE")
            print(f"📂 Playlists created: {playlists_created}")
            print(f"✅ Total tracks imported: {total_imported}")
            print(f"❌ Total failed: {total_failed}")
            if total_imported + total_failed > 0:
                success_rate = (total_imported / (total_imported + total_failed)) * 100
                print(f"📈 Success rate: {success_rate:.1f}%")
            
            # Show failed items summary and save report
            if total_failed > 0:
                self.print_failed_items_summary("playlist_tracks")
                self.save_failed_items_report("playlist_tracks")
                
        except Exception as e:
            print(f"❌ Error during playlists transfer: {e}")

    def direct_transfer_everything(self):
        """Transfer everything at once"""
        print("\n🚀 TRANSFERRING EVERYTHING")
        print("=" * 35)
        print("This will transfer: Songs, Artists, Albums, and Playlists")
        
        confirm = input("Continue? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Transfer cancelled")
            return
        
        if not self.spotify or not self.tidal:
            print("❌ Both services must be connected first")
            return
        
        # Reset stats and failed items
        self.transfer_stats = {
            'songs_imported': 0,
            'artists_imported': 0, 
            'albums_imported': 0,
            'playlists_created': 0,
            'total_failed': 0
        }
        self.failed_items = {
            'songs': [],
            'artists': [],
            'albums': [],
            'playlist_tracks': []
        }
        
        print("\n1/4 Transferring songs...")
        self.direct_transfer_songs()
        
        print("\n2/4 Transferring artists...")
        self.direct_transfer_artists()
        
        print("\n3/4 Transferring albums...")
        self.direct_transfer_albums()
        
        print("\n4/4 Transferring playlists...")
        self.direct_transfer_playlists()
        
        self.show_transfer_stats()

    def show_transfer_stats(self):
        """Show comprehensive transfer statistics"""
        print(f"\n{'='*60}")
        print(f"📊 COMPLETE TRANSFER STATISTICS")
        print(f"{'='*60}")
        print(f"🎵 Songs imported: {self.transfer_stats['songs_imported']}")
        print(f"👨‍🎤 Artists imported: {self.transfer_stats['artists_imported']}")
        print(f"💿 Albums imported: {self.transfer_stats['albums_imported']}")
        print(f"📂 Playlists created: {self.transfer_stats['playlists_created']}")
        print(f"❌ Total failed: {self.transfer_stats['total_failed']}")
        
        total_items = (self.transfer_stats['songs_imported'] + 
                      self.transfer_stats['artists_imported'] + 
                      self.transfer_stats['albums_imported'] + 
                      self.transfer_stats['total_failed'])
        
        if total_items > 0:
            success_rate = ((self.transfer_stats['songs_imported'] + 
                           self.transfer_stats['artists_imported'] + 
                           self.transfer_stats['albums_imported']) / total_items) * 100
            print(f"📈 Overall success rate: {success_rate:.1f}%")
        
        # Show overall failed items summary and save comprehensive report
        total_failed = sum(len(items) for items in self.failed_items.values())
        if total_failed > 0:
            self.print_failed_items_summary("all")
            self.save_failed_items_report("all")
        
        print(f"{'='*60}")

    def show_main_menu(self):
        """Display the main menu and handle user input"""
        print("\n🎵 SPOTIFY → TIDAL TRANSFER")
        print("=" * 50)
        print("1. 🔧 Setup Credentials")
        print("2. 🎵 Transfer Songs (Liked Songs)")
        print("3. 👨‍🎤 Transfer Artists (Followed Artists)")  
        print("4. 💿 Transfer Albums (Saved Albums)")
        print("5. 📋 Transfer Playlists")
        print("6. 🚀 Transfer Everything")
        print("")
        print("7. 🚫 Show Failed Items Report")
        print("8. 🧪 Test Connections")
        print("9. 📊 Show Transfer Statistics")
        print("")
        print("0. Exit")
        print("=" * 50)

    def run(self):
        """Main application loop"""        
        while True:
            self.show_main_menu()
            choice = input("\nSelect option: ").strip().lower()

            if choice == "1":
                self.setup_credentials_interactive()
            elif choice == "2":
                if not self.spotify or not self.tidal:
                    print("❌ Please setup credentials and connect to both services first (option 1 and 8)")
                    continue
                self.direct_transfer_songs()
            elif choice == "3":
                if not self.spotify or not self.tidal:
                    print("❌ Please setup credentials and connect to both services first (option 1 and 8)")
                    continue
                self.direct_transfer_artists()
            elif choice == "4":
                if not self.spotify or not self.tidal:
                    print("❌ Please setup credentials and connect to both services first (option 1 and 8)")
                    continue
                self.direct_transfer_albums()
            elif choice == "5":
                if not self.spotify or not self.tidal:
                    print("❌ Please setup credentials and connect to both services first (option 1 and 8)")
                    continue
                self.direct_transfer_playlists()
            elif choice == "6":
                if not self.spotify or not self.tidal:
                    print("❌ Please setup credentials and connect to both services first (option 1 and 8)")
                    continue
                self.direct_transfer_everything()
            elif choice == "7":
                self.print_failed_items_summary("all")
            elif choice == "8":
                self.test_connections()
            elif choice == "9":
                self.show_transfer_stats()
            elif choice == "0":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid option. Please try again.")
            
            input("\nPress Enter to continue...")


def main():
    """Main entry point"""
    print("🎵 Spotify to TIDAL Transfer Tool")
    print("Built with ❤️ for seamless music migration")
    print()
    
    # Load environment variables from .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # dotenv not required in cloud environments
    
    app = SpotifyTidalTransfer()
    app.run()


if __name__ == "__main__":
    main()