# About PE Helper
PE Helper is a Discord bot designed for NYP Piano Ensemble's server to provide music-related resources and aide in analytics.

&nbsp;
## Command Groups

### ⚙️ Admin
*/shutdown*
- Confirms with the admin on his/her decision.
- If confirmed, shuts down the bot.

*/restart*
- Restarts the bot.

*/reload*
- Provides admins an option to reload all cogs or a specified cog.

*/info*
- Displays real-time bot statistics.
- This includes uptime, memory usage, CPU load, and library versions (Python and discord.py).

&nbsp;
### 👑 EXCO-Exclusive
**/members-details*
- Exports details of all users to an Excel sheet.

*/weekly-session-nominal-rolls*
- Exports nominal rolls of all weekly sessions to Excel.

&nbsp;
### 👥 Members
*/list-current-exco*
- Lists names of those in the current EXCO.

*/list-piano-group-members*
- Creates a dropdown option, where the user can select a piano group and list its members (excl. alumni).

&nbsp;
### 🎶 Music
*/add-queue*
- Enables users to add songs to the queue by submitting a YouTube URL.
- Upon receiving the YouTube URL, the bot converts the video into a temporary audio file to be played in the order of the queue.

*/view-queue*
- Displays the songs in the queue.
- This includes the name of the song, its duration and YouTube URL.

*/vote-skip*
- Creates a custom poll for users to vote whether to skip the song currently playing in the queue.

&nbsp;
### 🔍 Score-Searcher
*/search-piece*
- Users may type in the name of the piece they want to search and select its associated composer from predefined options.
- Returns the top 10 URLs from IMSLP for the search, based on number of downloads, which the users may click to download the piece.

&nbsp;
### 📄 Sheet-Retriever
*/view-pe-sheets*
- Provides users an avenue to view music sheets available in PE's catalog.
- Displays available music sheets in the form of buttons which users may click to download his/her chosen sheet.

&nbsp;
### 📊 Stats
*/piano-groups*
- Creates a pie chart of piano-playing groups of current members (foundational, novice, intermediate, advanced).

*/message-stats*
- Creates a bar chart of total messages & word counts by user.

*/weekly-session-popularity*
- Creates a line chart showing the trends in room registrations for the current academic year.
