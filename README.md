# 🎵 Spotify to TIDAL Transfer Tool

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/YOUR_USERNAME/spotify2tidal-transfer)

A powerful, cloud-optimized solution for seamlessly migrating your music library from Spotify to TIDAL. Perfect for running in GitHub Codespaces with zero local setup required!

## ✨ Features

- **🚀 Direct Transfer**: No CSV files needed - transfers directly between services
- **🔧 Interactive Setup**: Guided credential setup for cloud environments  
- **🎯 Smart Search**: Enhanced matching with confidence scoring and fallback queries
- **📊 Real-time Progress**: Live progress tracking with detailed statistics
- **🚫 Failed Items Tracking**: Detailed reports on items that couldn't be transferred
- **☁️ Cloud-Ready**: Optimized for GitHub Codespaces and other cloud environments

## 🌟 What You Can Transfer

- **🎵 Songs**: Your liked songs → TIDAL favorites
- **👨‍🎤 Artists**: Followed artists → TIDAL artist favorites  
- **💿 Albums**: Saved albums → TIDAL album favorites
- **📋 Playlists**: All your playlists with tracks
- **🚀 Everything**: All of the above in one comprehensive transfer

## 🚀 Quick Start in GitHub Codespaces

### Option 1: One-Click Launch
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/YOUR_USERNAME/spotify2tidal-transfer)

### Option 2: Manual Setup
1. **Fork this repository** to your GitHub account
2. **Open in Codespaces**: Click the green "Code" button → "Codespaces" → "Create codespace"
3. **Wait for setup** (dependencies install automatically)
4. **Run the tool**:
   ```bash
   python spotify_tidal_transfer.py
   ```

## 🔑 Required Credentials

### Spotify API Setup
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/)
2. Create an app (any name works)
3. Copy your **Client ID** and **Client Secret**
4. Add redirect URI: `https://example.com/callback`

### TIDAL Account
- Just your regular TIDAL Premium account (no API keys needed)

## 📖 How to Use

### 1. **Setup Credentials** (Option 1)
- Enter your Spotify Client ID and Secret when prompted
   
### 2. **Test Connections** (Option 8)
- Verify both Spotify and TIDAL connections work
   
### 3. **Choose Transfer Type**:
- **Option 2**: Songs only (liked tracks)
- **Option 3**: Artists only (followed artists)
- **Option 4**: Albums only (saved albums)  
- **Option 5**: Playlists only (all playlists)
- **Option 6**: Everything at once

### 4. **Monitor Progress** ✨
- Real-time progress with match confidence scores
- Detailed statistics and failed items reports

## 🎯 Smart Matching Features

- **Text Normalization**: Automatically removes noise like "(feat.)", "[Remaster]"
- **Progressive Search**: Multiple fallback queries for better matches
- **Confidence Scoring**: Shows match quality (✅ >80%, ⚠️ 50-80%)  
- **Artist Similarity**: Smart matching for collaborations and variations
- **Duration Matching**: Uses track length for better accuracy

## 📊 Example Output

```
🎵 TRANSFERRING LIKED SONGS
═══════════════════════════════════

🔄 Processing batch 1 (50 songs)...
  ✅ Shape of You - Ed Sheeran (95%)
  ✅ Blinding Lights - The Weeknd (92%)
  ⚠️ Some Remix Song - Artist (67%)
  ❌ Obscure Track - Unknown Artist

📊 SONGS TRANSFER COMPLETE
✅ Successfully imported: 847
❌ Failed: 23
📈 Success rate: 97.4%

🚫 FAILED ITEMS SUMMARY
══════════════════════════
🎵 Songs: 23
  • Obscure Indie Track - Unknown Band
  • Live at Concert - Famous Artist
  • Rare B-Side - Old Band
  ... and 20 more

💡 Full details will be saved to a report file
📝 Failed items report saved: failed_items_songs_20251016_143052.txt
```

## 🚫 Failed Items Tracking

### Automatic Reports
After each transfer, you get:
- **Console Summary**: Quick overview of failed items
- **Detailed Report File**: Complete list with reasons for failures
- **Manual Search Tips**: Guidance for finding missing tracks

### Report Contents
- Track/artist/album names that couldn't be matched
- Specific reasons for failures (not found, low confidence, errors)
- Organized by category (songs, artists, albums, playlists)
- Search suggestions for manual follow-up

## 🛠 Technical Details

- **Python 3.11+** with modern async patterns
- **Enhanced Search Logic** with multiple fallback strategies
- **Session-based Credentials** (no file persistence in cloud)
- **Rate Limiting Protection** to avoid API blocks
- **Error Recovery** with detailed logging and reporting

## 🆘 Troubleshooting

### Common Issues

**"Invalid Client" Error**
- Double-check your Spotify Client ID and Secret
- Ensure redirect URI is exactly: `https://example.com/callback`

**TIDAL Login Issues**  
- Make sure you have TIDAL Premium
- Try updating: `pip install --upgrade tidalapi`

**Low Match Rates**
- This is normal for very niche music
- Check the confidence scores - lower scores mean uncertain matches
- Use the failed items report for manual verification

### Getting Help

Open an issue on GitHub with:
- Error messages (if any)
- What you were trying to transfer  
- Your Python version: `python --version`

## 📝 License

MIT License - Feel free to fork and modify!

## 🙏 Acknowledgments

- Built with [spotipy](https://github.com/spotipy-dev/spotipy) and [tidalapi](https://github.com/tidalapi/tidalapi)
- Optimized for GitHub Codespaces
- Created for seamless music migration

---

**Ready to migrate your music library? Fire up GitHub Codespaces and let's go! 🚀**

### 🔗 Quick Links
- [Create Codespace](https://codespaces.new/YOUR_USERNAME/spotify2tidal-transfer) 
- [Spotify Developer Dashboard](https://developer.spotify.com/)
- [Report Issues](https://github.com/YOUR_USERNAME/spotify2tidal-transfer/issues)