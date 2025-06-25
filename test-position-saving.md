# Position Saving Test Instructions

## How to Test Drag Position Saving

1. **Open the Pipeline Monitor**:
   ```bash
   # Make sure services are running
   cd /home/aoi/code/loomv2
   docker compose -f docker-compose.local.yml up -d

   # Open in browser: http://localhost:3000
   ```

2. **Test Position Saving**:
   - Open browser developer tools (F12) → Console tab
   - Drag any node to a new position
   - Look for console logs showing:
     ```
     Node drag stopped, saving position for: [nodeId] [position]
     Updating position for [nodeId]: [position]
     All positions after update: [all stored positions]
     ```

3. **Test Position Loading**:
   - Refresh the page (F5)
   - Look for console logs showing:
     ```
     Loaded positions from localStorage: [positions object]
     Restored position for [nodeId]: [position]
     ```
   - Verify the node stayed in its dragged position

4. **Verify Database Connections**:
   - Check that raw topics now show connections to TimescaleDB
   - Look for edges connecting these topics to the database:
     - `external.twitter.liked.raw`
     - `external.calendar.events.raw`
     - `external.email.events.raw`
     - `device.sensor.gps.raw`
     - `device.health.heartrate.raw`
     - `device.state.power.raw`

## Expected Behavior

✅ **Working**:
- Drag nodes → positions save to localStorage → page refresh → positions restored
- Console shows detailed logging of save/load operations
- Raw topics connected to database in visualization

❌ **Not Working**:
- Positions reset to default after page refresh
- No console logs when dragging
- Missing database connections for raw topics

## Technical Details

- **Storage Key**: `loom-pipeline-node-positions`
- **Event Handler**: `onNodeDragStop` in React Flow
- **Database Logic**: Modified PipelineBuilder to include raw topics that store data directly
