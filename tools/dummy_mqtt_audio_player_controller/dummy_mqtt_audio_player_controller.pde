// Main sketch file - MusicPlayerController.pde
import java.awt.Toolkit;
import java.awt.datatransfer.*;
import java.awt.event.KeyEvent;

import java.util.Locale;
import java.text.NumberFormat;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;

import mqtt.*;
import controlP5.*;

// Global instances
UIManager uiManager;
MQTTManager mqttManager;
PlayerStateManager playerState;
AudioTracker audioTracker;
LevelVisualizer levelVisualizer;
ConfigManager config;
ClipboardManager clipboardManager;

void setup() {
  size(640, 480);
  Locale.setDefault(Locale.US);
  surface.setAlwaysOnTop(true);
  noStroke();

  // Initialize managers
  config = new ConfigManager();
  uiManager = new UIManager(this, config); // Pass main sketch and config
  mqttManager = new MQTTManager(config, this); // Pass 'this' (main sketch) for MQTT callbacks
  playerState = new PlayerStateManager();
  audioTracker = new AudioTracker();
  levelVisualizer = new LevelVisualizer();
  clipboardManager = new ClipboardManager(config);

  // Setup UI
  uiManager.setup();
  uiManager.setControlsLocked(true);
}

void draw() {
  background(0);
  uiManager.draw();
  clipboardManager.handleScheduledCleanup();
  levelVisualizer.draw();
}

void mousePressed() {
  clipboardManager.onMousePressed();
}

void keyPressed() {
  clipboardManager.handleKeyPressed();
}

void keyReleased() {
  clipboardManager.handleKeyReleased();
}

void controlEvent(ControlEvent theEvent) {
  uiManager.handleControlEvent(theEvent);
}

// MQTT Callbacks
void clientConnected() {
  mqttManager.onClientConnected();
}

void messageReceived(String topic, byte[] payload) {
  mqttManager.onMessageReceived(topic, payload);
}

void connectionLost() {
  mqttManager.onConnectionLost();
}

// UI Callbacks
void player_toggle(boolean flag) {
  uiManager.onPlayerToggle(flag);
}

void session_toggle(boolean flag) {
  uiManager.onSessionToggle(flag);
}

void loop_toggle(boolean flag) {
  uiManager.onLoopToggle(flag);
}

void volume_slider(float value) {
  uiManager.onVolumeSlider(value);
}

void send_audio_url() {
  uiManager.onSendAudioUrl();
}

void mqtt_toggle(boolean flag) {
  uiManager.onMqttToggle(flag);
}

void audio_tracker(float value) {
  uiManager.onAudioTracker(value);
}


void ch_1(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_2(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_3(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_4(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_5(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_6(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_7(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_8(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_9(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_10(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_11(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_12(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_13(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_14(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_15(boolean flag) {
  uiManager.onChannelToggle(flag);
}
void ch_16(boolean flag) {
  uiManager.onChannelToggle(flag);
}


// ===== CONFIGURATION MANAGER =====
class ConfigManager {
  // MQTT Configuration
  private String mqttHost = "127.0.0.1";
  private String mqttPort = "1883";
  private String mqttClientId = "processing_music_player_dummy_controller" + str(millis());
  private String targetClientId = "music_player";

  // Audio Configuration
  private String audioFileUrl = "https://zigzaggmbh.github.io/txt_to_music_samples_viewer/assets/medium_stereo_5sec_r1.wav";

  // UI Layout Constants
  private final int TOGGLE_BTN_START_X = 40;
  private final int TOGGLE_BTN_START_Y = 50;
  private final int TOGGLE_BTN_SIZE = 40;
  private final int VERTICAL_SPACING = 20;
  private final int HORIZONTAL_SPACING = 20;

  // Colors
  private final int BACKGROUND_COLOR = color(25);
  private final int SELECTED_COLOR = color(50, 50, 0);
  private final int ACTIVE_COLOR = color(100, 220, 120);

  // OS Detection
  private String currentOS;

  public ConfigManager() {
    currentOS = System.getProperty("os.name").toLowerCase();
    println("Operating System: " + currentOS);
  }

  // Getters
  public String getMqttHost() {
    return mqttHost;
  }
  public String getMqttPort() {
    return mqttPort;
  }
  public String getMqttClientId() {
    return mqttClientId;
  }
  public String getTargetClientId() {
    return targetClientId;
  }
  public String getAudioFileUrl() {
    return audioFileUrl;
  }
  public String getCurrentOS() {
    return currentOS;
  }

  public int getToggleBtnStartX() {
    return TOGGLE_BTN_START_X;
  }
  public int getToggleBtnStartY() {
    return TOGGLE_BTN_START_Y;
  }
  public int getToggleBtnSize() {
    return TOGGLE_BTN_SIZE;
  }
  public int getVerticalSpacing() {
    return VERTICAL_SPACING;
  }
  public int getHorizontalSpacing() {
    return HORIZONTAL_SPACING;
  }

  public int getBackgroundColor() {
    return BACKGROUND_COLOR;
  }
  public int getSelectedColor() {
    return SELECTED_COLOR;
  }
  public int getActiveColor() {
    return ACTIVE_COLOR;
  }

  // Setters
  public void setMqttHost(String host) {
    this.mqttHost = host;
  }
  public void setMqttPort(String port) {
    this.mqttPort = port;
  }
  public void setTargetClientId(String id) {
    this.targetClientId = id;
  }
  public void setAudioFileUrl(String url) {
    this.audioFileUrl = url;
  }

  public boolean isMacOS() {
    return currentOS.contains("mac");
  }
}

// ===== PLAYER STATE MANAGER =====
class PlayerStateManager {
  private String currentPlayerState = "";
  private boolean updatingFromMQTT = false;

  public String getCurrentPlayerState() {
    return currentPlayerState;
  }
  public boolean isUpdatingFromMQTT() {
    return updatingFromMQTT;
  }

  public void setUpdatingFromMQTT(boolean updating) {
    this.updatingFromMQTT = updating;
  }

  public void handlePlayerStateChange(String newState) {
    if (!newState.equals(currentPlayerState)) {
      println("Player state changed: '" + currentPlayerState + "' -> '" + newState + "'");
      currentPlayerState = newState;

      uiManager.syncPlayerToggle(newState);

      if (newState.equals("playing") || newState.equals("paused")) {
        uiManager.syncSessionToggle(newState);
      }
    }
  }

  public void reset() {
    currentPlayerState = "";
    updatingFromMQTT = false;
  }
}

// ===== AUDIO TRACKER =====
class AudioTracker {
  private float audioDurationSeconds = 0;
  private float audioPositionSeconds = 0;
  private String currentAudioFile = "";
  private String lastKnownAudioFile = "";
  private boolean updatingAudioTracker = false;

  public void handleAudioPositionUpdate(JSONObject json) {
    if (json == null) return;

    try {
      updatingAudioTracker = true;

      String position = json.getString("position", "00:00");
      String totalDuration = json.getString("total_duration", "00:00");
      String currentFile = json.getString("current_file", "");
      float receivedPercentage = json.getFloat("percentage", 0.0);

      audioPositionSeconds = parseTimeToSeconds(position);
      audioDurationSeconds = parseTimeToSeconds(totalDuration);
      currentAudioFile = currentFile;

      uiManager.updateAudioTracker(audioDurationSeconds, currentFile, receivedPercentage);

      if (!currentFile.equals(lastKnownAudioFile)) {
        lastKnownAudioFile = currentFile;
      }
    }
    catch (Exception e) {
      println("Error handling audio position update: " + e.getMessage());
    }
    finally {
      updatingAudioTracker = false;
    }
  }

  private float parseTimeToSeconds(String timeStr) {
    try {
      if (timeStr == null || timeStr.length() == 0) return 0;

      String[] parts = timeStr.split(":");
      if (parts.length == 2) {
        int minutes = Integer.parseInt(parts[0]);
        int seconds = Integer.parseInt(parts[1]);
        return minutes * 60 + seconds;
      } else if (parts.length == 3) {
        int hours = Integer.parseInt(parts[0]);
        int minutes = Integer.parseInt(parts[1]);
        int seconds = Integer.parseInt(parts[2]);
        return hours * 3600 + minutes * 60 + seconds;
      }

      return Float.parseFloat(timeStr);
    }
    catch (Exception e) {
      println("Error parsing time '" + timeStr + "': " + e.getMessage());
      return 0;
    }
  }

  public String formatTime(float totalSeconds) {
    if (totalSeconds < 0) return "00:00";

    int minutes = (int)(totalSeconds / 60);
    int seconds = (int)(totalSeconds % 60);
    return String.format("%02d:%02d", minutes, seconds);
  }

  public boolean isUpdatingAudioTracker() {
    return updatingAudioTracker;
  }
  public float getAudioDurationSeconds() {
    return audioDurationSeconds;
  }
  public float getAudioPositionSeconds() {
    return audioPositionSeconds;
  }
  public String getCurrentAudioFile() {
    return currentAudioFile;
  }

  public void reset() {
    audioDurationSeconds = 0;
    audioPositionSeconds = 0;
    currentAudioFile = "";
    lastKnownAudioFile = "";
    updatingAudioTracker = false;
  }
}

// ===== LEVEL VISUALIZER =====
class LevelVisualizer {
  private float currentAudioLevel = 0.0;
  private float lastLevelUpdateTime = 0;
  private boolean levelDataReceived = false;
  private float smoothedAudioLevel = 0.0;
  private float peakAudioLevel = 0.0;
  private int lastPeakUpdateTime = 0;

  // Configuration
  private final boolean LEVEL_METER_SMOOTHING = true;
  private final boolean LEVEL_METER_PEAK_HOLD = true;
  private final float LEVEL_SMOOTHING_SPEED = 0.15f;
  private final float PEAK_DECAY_RATE = 0.02f;

  public void handleAudioLevelUpdate(JSONObject json) {
    if (json == null) return;

    try {
      if (json.hasKey("level")) {
        currentAudioLevel = json.getFloat("level");
        lastLevelUpdateTime = millis();
        levelDataReceived = true;
      }
    }
    catch (Exception e) {
      println("Error handling audio level update: " + e.getMessage());
    }
  }

  public void draw() {
    drawLevelMeter();
  }

  private void drawLevelMeter() {
    // Get audio tracker position for relative positioning
    float[] trackerPos = uiManager.getAudioTrackerPosition();

    pushMatrix();
    translate(trackerPos[0] + trackerPos[2] + 10, trackerPos[1] - 90);

    // Check for stale data
    if (millis() - lastLevelUpdateTime > 3000) {
      levelDataReceived = false;
      currentAudioLevel = 0.0;
    }

    // Level meter settings
    int barWidth = 10;
    int barHeight = 100;
    int numSegments = 20;
    int segmentHeight = (barHeight - (numSegments - 1)) / numSegments;
    int segmentGap = 1;

    // Process current level
    float scaledLevel = constrain(currentAudioLevel * 25, 0, 1);

    // Apply smoothing
    if (LEVEL_METER_SMOOTHING) {
      smoothedAudioLevel = lerp(smoothedAudioLevel, scaledLevel, LEVEL_SMOOTHING_SPEED);
    } else {
      smoothedAudioLevel = scaledLevel;
    }

    // Update peak hold
    if (LEVEL_METER_PEAK_HOLD && levelDataReceived) {
      if (scaledLevel > peakAudioLevel) {
        peakAudioLevel = scaledLevel;
        lastPeakUpdateTime = millis();
      } else if (millis() - lastPeakUpdateTime > 100) {
        peakAudioLevel = max(0, peakAudioLevel - PEAK_DECAY_RATE);
      }
    }

    // Calculate segments
    int activeSegments = int(smoothedAudioLevel * numSegments);
    int peakSegment = LEVEL_METER_PEAK_HOLD ? int(peakAudioLevel * numSegments) : 0;

    // Draw background
    stroke(100);
    noFill();
    rect(-1, 4, barWidth + 2, barHeight + 2);

    // Draw segments
    for (int i = 0; i < numSegments; i++) {
      int segmentY = 5 + (barHeight - (i + 1) * (segmentHeight + segmentGap));
      drawSegment(i, segmentY, segmentHeight, barWidth, activeSegments,
        peakSegment, numSegments);
    }

    popMatrix();
  }

  private void drawSegment(int i, int segmentY, int segmentHeight, int barWidth,
    int activeSegments, int peakSegment, int numSegments) {
    if (i < activeSegments && levelDataReceived) {
      // Active segment
      noStroke();
      fill(getSegmentColor(i, numSegments, false));
      rect(0, segmentY, barWidth, segmentHeight);
    } else if (LEVEL_METER_PEAK_HOLD && i == peakSegment && peakSegment > activeSegments) {
      // Peak hold segment
      noStroke();
      fill(getSegmentColor(i, numSegments, true));
      rect(0, segmentY, barWidth, segmentHeight);
    } else {
      // Inactive segment
      fill(30);
      noStroke();
      rect(0, segmentY, barWidth, segmentHeight);
    }
  }

  private color getSegmentColor(int segment, int numSegments, boolean dimmed) {
    int alpha = dimmed ? 128 : 255;

    if (segment < (numSegments * 0.6)) {
      return color(0, alpha, 0); // Green
    } else if (segment < numSegments * 0.8) {
      return color(alpha, alpha, 0); // Yellow
    } else {
      return color(alpha, 0, 0); // Red
    }
  }

  public void reset() {
    currentAudioLevel = 0.0;
    levelDataReceived = false;
    smoothedAudioLevel = 0.0;
    peakAudioLevel = 0.0;
  }
}

// ===== MQTT MANAGER =====
class MQTTManager {
  private MQTTClient client;
  private ConfigManager config;
  private boolean mqttConnected = false;
  private String mqttStatus = "Disconnected";

  // Topic templates
  private String healthSubTopic = "";
  private String stateSubTopic = "";
  private String audioPositionSubTopic = "";
  private String audioLevelSubTopic = "";

  public MQTTManager(ConfigManager config, PApplet sketch) {
    this.config = config;
    client = new MQTTClient(sketch); // Pass main sketch for callbacks
  }

  public void connect() {
    if (!mqttConnected) {
      try {
        updateTopics();
        String brokerUrl = "mqtt://" + config.getMqttHost() + ":" + config.getMqttPort();
        println("Attempting to connect to: " + brokerUrl);
        client.connect(brokerUrl, config.getMqttClientId(), true);
        mqttStatus = "Connecting...";
      }
      catch (Exception e) {
        println("Failed to connect to MQTT: " + e.getMessage());
        uiManager.resetMqttToggle();
        mqttStatus = "Failed";
      }
    }
  }

  public void disconnect() {
    if (mqttConnected) {
      try {
        client.disconnect();
        mqttConnected = false;
        mqttStatus = "Disconnected";
        println("Disconnected from MQTT");

        resetTopics();
        playerState.reset();
        audioTracker.reset();
        levelVisualizer.reset();

        uiManager.setControlsLocked(true);
      }
      catch (Exception e) {
        println("Error disconnecting from MQTT: " + e.getMessage());
        mqttStatus = "Error Disconnecting";
      }
    }
  }

  private void updateTopics() {
    String targetId = config.getTargetClientId();
    healthSubTopic = "service/" + targetId + "/status/health";
    stateSubTopic = "service/" + targetId + "/status/state";
    audioPositionSubTopic = "service/" + targetId + "/status/audio/position";
    audioLevelSubTopic = "service/" + targetId + "/status/audio/level";
  }

  private void resetTopics() {
    healthSubTopic = "";
    stateSubTopic = "";
    audioPositionSubTopic = "";
    audioLevelSubTopic = "";
  }

  public void onClientConnected() {
    println("MQTT client connected to " + config.getMqttHost() + ":" + config.getMqttPort());
    mqttConnected = true;
    mqttStatus = "Connected";

    uiManager.setMqttToggleValue(true);
    uiManager.setControlsLocked(false);

    // Subscribe to topics
    client.subscribe(stateSubTopic);
    client.subscribe(healthSubTopic);
    client.subscribe(audioPositionSubTopic);
    client.subscribe(audioLevelSubTopic);

    println("Subscribed to topics:");
    println(" " + stateSubTopic);
    println(" " + healthSubTopic);
    println(" " + audioPositionSubTopic);
    println(" " + audioLevelSubTopic);
  }

  public void onConnectionLost() {
    println("MQTT connection lost");
    mqttConnected = false;
    mqttStatus = "Disconnected";

    resetTopics();
    playerState.reset();
    audioTracker.reset();

    uiManager.resetMqttToggle();
    uiManager.setControlsLocked(true);
  }

  public void onMessageReceived(String topic, byte[] payload) {
    String message = new String(payload);

    if (topic.equals(stateSubTopic)) {
      parsePlayerStatus(message);
    } else if (topic.equals(healthSubTopic)) {
      parsePlayerHealth(message);
    } else if (topic.equals(audioPositionSubTopic)) {
      audioTracker.handleAudioPositionUpdate(parseJSONObject(message));
    } else if (topic.equals(audioLevelSubTopic)) {
      levelVisualizer.handleAudioLevelUpdate(parseJSONObject(message));
    }
  }

  private void parsePlayerStatus(String jsonMessage) {
    try {
      JSONObject json = parseJSONObject(jsonMessage);
      if (json != null) {
        playerState.setUpdatingFromMQTT(true);

        String newState = json.getString("state", "");
        if (newState.length() > 0) {
          playerState.handlePlayerStateChange(newState);
        }

        uiManager.handleLoopEnabledChange(json);
        uiManager.handleVolumeChange(json);

        playerState.setUpdatingFromMQTT(false);
      }
    }
    catch (Exception ex) {
      playerState.setUpdatingFromMQTT(false);
      println("Error parsing player status: " + ex.getMessage());
    }
  }

  private void parsePlayerHealth(String jsonMessage) {
    try {
      JSONObject json = parseJSONObject(jsonMessage);
      if (json != null) {
        playerState.setUpdatingFromMQTT(true);

        String status = json.getString("status", "");
        if (status.equals("offline")) {
          uiManager.handlePlayerOffline();
        } else if (status.equals("online")) {
          uiManager.handlePlayerOnline();
        }

        playerState.setUpdatingFromMQTT(false);
      }
    }
    catch (Exception ex) {
      playerState.setUpdatingFromMQTT(false);
      println("Error parsing player health: " + ex.getMessage());
    }
  }

  public void publishCommand(String command, String payload) {
    if (mqttConnected) {
      String topic = "/" + config.getTargetClientId() + "/cmd/" + command;
      client.publish(topic, payload);
    }
  }

  public void publishAudioUrl(String url) {
    if (mqttConnected) {
      String topic = "/" + config.getTargetClientId() + "/audio_url";
      client.publish(topic, url);
    }
  }

  public boolean isConnected() {
    return mqttConnected;
  }
  public String getStatus() {
    return mqttStatus;
  }
}

// ===== CLIPBOARD MANAGER =====
class ClipboardManager {
  private ConfigManager config;
  private boolean isCtrlPressed = false;
  private boolean isCmdPressed = false;
  private boolean textWasSelected = false;
  private boolean fieldIsSelected = false;
  private String selectedFieldName = "";

  // Cleanup handling
  private char pendingCleanupChar = 0;
  private int cleanupScheduledTime = 0;
  private boolean cleanupPending = false;

  public ClipboardManager(ConfigManager config) {
    this.config = config;
  }

  public void handleKeyPressed() {
    // Track modifier keys
    if (config.isMacOS()) {
      if (key == CODED && keyCode == KeyEvent.VK_META) {
        isCmdPressed = true;
        return;
      }
    } else {
      if (key == CODED && keyCode == KeyEvent.VK_CONTROL) {
        isCtrlPressed = true;
        return;
      }
    }

    // Check if we're doing a clipboard operation
    boolean modifierHeld = config.isMacOS() ? isCmdPressed : isCtrlPressed;
    Textfield activeField = uiManager.getActiveTextField();

    if (activeField != null && modifierHeld) {
      switch (key) {
      case 'c':
      case 'C':
        copyFromActiveTextField();
        return;
      case 'v':
      case 'V':
        pasteToActiveTextField();
        return;
      case 'x':
      case 'X':
        cutFromActiveTextField();
        return;
      case 'a':
      case 'A':
        selectAllInActiveTextField();
        return;
      }
    }

    // Handle other special keys for active text field
    if (activeField != null) {
      if (key == BACKSPACE) {
        handleBackspaceAfterSelectAll(activeField);
      }
      // Don't prevent normal text input - let ControlP5 handle it
    }
  }

  public void handleKeyReleased() {
    if (config.isMacOS()) {
      if (key == CODED && keyCode == KeyEvent.VK_META) {
        isCmdPressed = false;
      }
    } else {
      if (key == CODED && keyCode == KeyEvent.VK_CONTROL) {
        isCtrlPressed = false;
      }
    }
  }

  public void onMousePressed() {
    if (fieldIsSelected) {
      resetAllSelection();
    }
  }

  private void copyFromActiveTextField() {
    try {
      Textfield activeField = uiManager.getActiveTextField();
      if (activeField != null) {
        String text = activeField.getText();
        if (text.length() > 0) {
          StringSelection stringSelection = new StringSelection(text);
          Clipboard clipboard = Toolkit.getDefaultToolkit().getSystemClipboard();
          clipboard.setContents(stringSelection, null);
          println("✓ Copied: " + text);

          resetAllSelection();
          scheduleCharCleanup('c');
        }
      }
    }
    catch (Exception e) {
      println("Copy failed: " + e.getMessage());
    }
  }

  private void pasteToActiveTextField() {
    try {
      Textfield activeField = uiManager.getActiveTextField();
      if (activeField != null) {
        Clipboard clipboard = Toolkit.getDefaultToolkit().getSystemClipboard();
        Transferable contents = clipboard.getContents(null);
        if (contents != null && contents.isDataFlavorSupported(DataFlavor.stringFlavor)) {
          String text = (String) contents.getTransferData(DataFlavor.stringFlavor);
          activeField.setText(text);
          uiManager.updateGlobalVariables(activeField.getName(), text);
          println("Pasted: " + text);

          resetAllSelection();
          scheduleCharCleanup('v');
        }
      }
    }
    catch (Exception e) {
      println("Paste failed: " + e.getMessage());
    }
  }

  private void cutFromActiveTextField() {
    try {
      Textfield activeField = uiManager.getActiveTextField();
      if (activeField != null) {
        String text = activeField.getText();
        if (text.length() > 0) {
          StringSelection stringSelection = new StringSelection(text);
          Clipboard clipboard = Toolkit.getDefaultToolkit().getSystemClipboard();
          clipboard.setContents(stringSelection, null);

          activeField.setText("");
          uiManager.updateGlobalVariables(activeField.getName(), "");
          println("✂ Cut: " + text);

          resetAllSelection();
          scheduleCharCleanup('x');
        }
      }
    }
    catch (Exception e) {
      println("Cut failed: " + e.getMessage());
    }
  }

  private void selectAllInActiveTextField() {
    try {
      Textfield activeField = uiManager.getActiveTextField();
      if (activeField != null) {
        String text = activeField.getText();
        if (text.length() > 0) {
          StringSelection stringSelection = new StringSelection(text);
          Clipboard clipboard = Toolkit.getDefaultToolkit().getSystemClipboard();
          clipboard.setContents(stringSelection, null);

          textWasSelected = true;
          setFieldSelected(activeField.getName());

          println("Selected all in: " + activeField.getName());
          scheduleCharCleanup('a');
        }
      }
    }
    catch (Exception e) {
      // Handle silently
    }
  }

  private void handleBackspaceAfterSelectAll(Textfield field) {
    if (textWasSelected && field != null) {
      field.setText("");
      uiManager.updateGlobalVariables(field.getName(), "");
      println("Deleted selected text");
      resetAllSelection();
    }
  }

  private void setFieldSelected(String fieldName) {
    resetAllSelection();

    try {
      Textfield field = uiManager.getTextfield(fieldName);
      if (field != null) {
        field.setColorBackground(config.getSelectedColor());
        fieldIsSelected = true;
        selectedFieldName = fieldName;
        println("Selected field: " + fieldName);
      }
    }
    catch (Exception e) {
      println("Failed to select field: " + fieldName);
    }
  }

  private void resetAllSelection() {
    if (fieldIsSelected) {
      try {
        Textfield field = uiManager.getTextfield(selectedFieldName);
        if (field != null) {
          field.setColorBackground(config.getBackgroundColor());
        }
      }
      catch (Exception e) {
        // Field might not exist
      }

      fieldIsSelected = false;
      selectedFieldName = "";
      textWasSelected = false;
    }
  }

  private void scheduleCharCleanup(char unwantedChar) {
    pendingCleanupChar = unwantedChar;
    cleanupScheduledTime = millis() + 1;
    cleanupPending = true;
  }

  public void handleScheduledCleanup() {
    if (cleanupPending && millis() >= cleanupScheduledTime) {
      Textfield activeField = uiManager.getActiveTextField();
      if (activeField != null) {
        String text = activeField.getText();
        if (text.length() > 0) {
          char lastChar = text.charAt(text.length() - 1);
          if (lastChar == pendingCleanupChar ||
            lastChar == Character.toUpperCase(pendingCleanupChar)) {
            String cleanText = text.substring(0, text.length() - 1);
            activeField.setText(cleanText);
            uiManager.updateGlobalVariables(activeField.getName(), cleanText);
          }
        }
      }

      cleanupPending = false;
      pendingCleanupChar = 0;
    }
  }
}

// ===== UI MANAGER =====
class UIManager {
  private ControlP5 cp5;
  private Textlabel fileName;
  private Textarea consoleTextarea;
  private Println console;
  private PApplet sketch;
  private ConfigManager config;

  public UIManager(PApplet sketch, ConfigManager config) {
    this.sketch = sketch;
    this.config = config;
  }

  public void setup() {
    cp5 = new ControlP5(sketch); // Pass main sketch to ControlP5
    createUIElements();
  }

  private void createUIElements() {
    int startX = config.getToggleBtnStartX();
    int startY = config.getToggleBtnStartY();
    int btnSize = config.getToggleBtnSize();
    int hSpacing = config.getHorizontalSpacing();
    int bgColor = config.getBackgroundColor();
    int fgColor = color(150, 120, 120);
    int activeColor = config.getActiveColor();

    // Target client ID
    cp5.addTextfield("target_client_id")
      .setLabel("Target Client ID")
      .setPosition(startX, 5)
      .setSize(120, 25)
      .setText(config.getTargetClientId())
      .setColorBackground(bgColor)
      .setColorForeground(fgColor)
      .setColorActive(color(10))
      .setAutoClear(false); // Prevent clearing on Enter

    // MQTT Host
    cp5.addTextfield("mqtt_host")
      .setLabel("MQTT Host IP")
      .setPosition(startX, startY)
      .setSize(120, 25)
      .setText(config.getMqttHost())
      .setColorBackground(bgColor)
      .setColorForeground(fgColor)
      .setColorActive(color(10))
      .setAutoClear(false); // Prevent clearing on Enter

    // MQTT Port
    cp5.addTextfield("mqtt_port")
      .setLabel("MQTT Port")
      .setPosition(startX + 120 + hSpacing, startY)
      .setSize(50, 25)
      .setText(config.getMqttPort())
      .setColorBackground(bgColor)
      .setColorForeground(fgColor)
      .setColorActive(color(10))
      .setAutoClear(false); // Prevent clearing on Enter

    // MQTT Toggle
    cp5.addToggle("mqtt_toggle")
      .setLabel("MQTT - connect / disconnect")
      .setPosition(startX + 120 + hSpacing + 50 + hSpacing, startY)
      .setSize(25, 25)
      .setColorBackground(color(50))
      .setColorForeground(activeColor)
      .setColorActive(activeColor);

    // Console
    float consoleX = cp5.get(Toggle.class, "mqtt_toggle").getPosition()[0] + 140 ;
    float consoleY = 5;
    consoleTextarea = cp5.addTextarea("txt")
      .setPosition(consoleX, consoleY)
      .setSize(242, 150)
      .setLineHeight(14)
      .setColor(color(200))
      .setColorBackground(color(200, 80))
      .setColorForeground(color(255, 100));
    console = cp5.addConsole(consoleTextarea);

    // Audio URL
    cp5.addTextfield("audio_url")
      .setLabel("Audio file url")
      .setPosition(startX, startY + 100)
      .setSize(185, 25)
      .setText(config.getAudioFileUrl())
      .setColorBackground(bgColor)
      .setColorForeground(fgColor)
      .setColorActive(color(10))
      .setAutoClear(false); // Prevent clearing on Enter

    // Send button
    cp5.addBang("send_audio_url")
      .setLabel("send")
      .setPosition(startX + 120 + hSpacing + 50 + hSpacing, startY + 100)
      .setSize(25, 25)
      .setColorBackground(color(50))
      .setColorForeground(color(50))
      .setColorActive(activeColor);

    // Audio tracker
    cp5.addSlider("audio_tracker")
      .setLabel("")
      .setPosition(startX, startY + 200)
      .setSize(545, 10)
      .setRange(0, 1)
      .setValue(0.0)
      .setColorBackground(color(50))
      .setColorForeground(activeColor)
      .setColorActive(activeColor);

    // File name label
    fileName = cp5.addTextlabel("file_name")
      .setText("AUDIO_FILE:")
      .setPosition(startX - 4, startY + 220);

    // Player controls
    createPlayerControls(startX, startY + 250, btnSize, activeColor);

    // Channel Section label
    float channel_label_posX = cp5.get(Toggle.class, "player_toggle").getPosition()[0];
    float channel_label_posY = cp5.get(Toggle.class, "player_toggle").getPosition()[1] + cp5.get(Toggle.class, "player_toggle").getHeight() + 90;
    cp5.addTextlabel("Channel_mask_label")
      .setText("CHANNEL MASKS")
      .setPosition(channel_label_posX - 4, channel_label_posY);
  }

  private void createPlayerControls(int x, int y, int btnSize, int activeColor) {
    // Player toggle
    cp5.addToggle("player_toggle")
      .setLabel("PLAYER - start / stop")
      .setPosition(x, y)
      .setSize(btnSize, btnSize)
      .setColorBackground(color(50))
      .setColorForeground(activeColor)
      .setColorActive(activeColor);

    // Session toggle
    cp5.addToggle("session_toggle")
      .setLabel("SESSION - play / pause")
      .setPosition(x + 100 + btnSize, y)
      .setSize(btnSize, btnSize)
      .setColorBackground(color(50))
      .setColorForeground(activeColor)
      .setColorActive(activeColor);

    // Loop toggle
    cp5.addToggle("loop_toggle")
      .setLabel("LOOP - enable / disable")
      .setPosition(x + 200 + btnSize * 2, y)
      .setSize(btnSize, btnSize)
      .setColorBackground(color(50))
      .setColorForeground(activeColor)
      .setColorActive(activeColor);

    // Volume slider
    cp5.addSlider("volume_slider")
      .setLabel("VOLUME")
      .setPosition(x + 300 + btnSize * 3, y)
      .setSize(125, 15)
      .setRange(0, 1)
      .setValue(0.5)
      .setColorBackground(color(50))
      .setColorForeground(activeColor)
      .setColorActive(activeColor);

    // Channel mask controls
    int total_channels = 16;
    float start_posX = cp5.get(Toggle.class, "player_toggle").getPosition()[0];
    float start_posY = cp5.get(Toggle.class, "player_toggle").getPosition()[1] + cp5.get(Toggle.class, "player_toggle").getHeight() + 50;
    for (int i=0; i<total_channels; i++) {
      String ch_ctrl_bang_name = "ch_"+str(i+1);
      cp5.addToggle(ch_ctrl_bang_name)
        .setLabel(str(i+1))
        .setSize(15, 15)
        .setColorBackground(color(50))
        .setColorForeground(activeColor)
        .setColorActive(activeColor)
        .setPosition(start_posX + i*15*2, start_posY);
    }
  }

  public void draw() {
    fill(255);
    textSize(12);
    text("MQTT STATUS: " + mqttManager.getStatus(), 39,
      config.getToggleBtnStartY() + 60);
  }

  public void lockChannelControls(boolean locked) {
    for (int i = 1; i <= 16; i++) {
      String toggleName = "ch_" + i;
      cp5.getController(toggleName).setLock(locked);
    }
  }

  public void setControlsLocked(boolean locked) {
    cp5.getController("player_toggle").setLock(locked);
    cp5.getController("session_toggle").setLock(locked);
    cp5.getController("loop_toggle").setLock(locked);
    cp5.getController("volume_slider").setLock(locked);
    cp5.getController("audio_url").setLock(locked);
    cp5.getController("send_audio_url").setLock(locked);
    cp5.getController("audio_tracker").setLock(locked);

    // Connection fields (opposite of controls)
    cp5.getController("mqtt_host").setLock(!locked);
    cp5.getController("mqtt_port").setLock(!locked);
    cp5.getController("target_client_id").setLock(!locked);

    lockChannelControls(locked);
  }

  // Event handlers
  public void onPlayerToggle(boolean flag) {
    if (playerState.isUpdatingFromMQTT()) return;
    if (!mqttManager.isConnected()) return;

    String command = flag ? "start" : "stop";
    mqttManager.publishCommand("player", command);
    println(command + " player");
  }

  public void onSessionToggle(boolean flag) {
    if (playerState.isUpdatingFromMQTT()) return;
    if (!mqttManager.isConnected()) return;

    String command = flag ? "play" : "pause";
    mqttManager.publishCommand("session", command);
    println(command + " session");
  }

  public void onLoopToggle(boolean flag) {
    if (playerState.isUpdatingFromMQTT()) return;
    if (!mqttManager.isConnected()) return;

    String command = flag ? "True" : "False";
    mqttManager.publishCommand("loop", command);
    println((flag ? "enable" : "disable") + " loop");
  }

  public void onVolumeSlider(float value) {
    if (playerState.isUpdatingFromMQTT()) return;
    if (!mqttManager.isConnected()) return;

    String volumePayload = String.format("%.2f", value);
    mqttManager.publishCommand("volume", volumePayload);
    println("Volume changed to: " + volumePayload);
  }

  public void onSendAudioUrl() {
    if (!mqttManager.isConnected()) return;

    // Get current value from text field
    String audioUrl = cp5.get(Textfield.class, "audio_url").getText();
    if (audioUrl.length() > 0) {
      mqttManager.publishAudioUrl(audioUrl);
      println("Sent audio URL via MQTT: " + audioUrl);
    }
  }

  public void onMqttToggle(boolean flag) {
    if (flag) {
      // Update config with current text field values before connecting
      updateConfigFromTextFields();
      mqttManager.connect();
    } else {
      mqttManager.disconnect();
    }
  }

  public void onAudioTracker(float value) {
    if (audioTracker.isUpdatingAudioTracker()) return;
    if (!mqttManager.isConnected()) return;

    String seekPayload = String.format("%.1f", value) + "%";
    mqttManager.publishCommand("seek", seekPayload);
    println("User seek to: " + seekPayload);
  }

  public void handleControlEvent(ControlEvent theEvent) {
    String name = theEvent.getController().getName();
    String value = theEvent.getController().getStringValue();

    // Always update config when text fields change (removed the MQTT connected check)
    if (name.equals("mqtt_host")) {
      config.setMqttHost(value);
      println("MQTT Host updated to: " + value);
    } else if (name.equals("mqtt_port")) {
      config.setMqttPort(value);
      println("MQTT Port updated to: " + value);
    } else if (name.equals("target_client_id")) {
      config.setTargetClientId(value);
      println("Target Client ID updated to: " + value);
    } else if (name.equals("audio_url")) {
      config.setAudioFileUrl(value);
      println("Audio URL updated to: " + value);
    }
  }

  // Helper method to update config from current text field values
  private void updateConfigFromTextFields() {
    config.setMqttHost(cp5.get(Textfield.class, "mqtt_host").getText());
    config.setMqttPort(cp5.get(Textfield.class, "mqtt_port").getText());
    config.setTargetClientId(cp5.get(Textfield.class, "target_client_id").getText());
    config.setAudioFileUrl(cp5.get(Textfield.class, "audio_url").getText());
  }

  // Utility methods
  public Textfield getActiveTextField() {
    if (cp5.get(Textfield.class, "target_client_id").isFocus()) {
      return cp5.get(Textfield.class, "target_client_id");
    }
    if (cp5.get(Textfield.class, "mqtt_host").isFocus()) {
      return cp5.get(Textfield.class, "mqtt_host");
    }
    if (cp5.get(Textfield.class, "mqtt_port").isFocus()) {
      return cp5.get(Textfield.class, "mqtt_port");
    }
    if (cp5.get(Textfield.class, "audio_url").isFocus()) {
      return cp5.get(Textfield.class, "audio_url");
    }
    return null;
  }

  public Textfield getTextfield(String name) {
    return cp5.get(Textfield.class, name);
  }

  public void updateGlobalVariables(String fieldName, String value) {
    if (fieldName.equals("mqtt_host")) {
      config.setMqttHost(value);
    } else if (fieldName.equals("mqtt_port")) {
      config.setMqttPort(value);
    } else if (fieldName.equals("target_client_id")) {
      config.setTargetClientId(value);
    } else if (fieldName.equals("audio_url")) {
      config.setAudioFileUrl(value);
    }
  }

  public float[] getAudioTrackerPosition() {
    Slider audioTracker = cp5.get(Slider.class, "audio_tracker");
    return new float[] {
      audioTracker.getPosition()[0],
      audioTracker.getPosition()[1],
      audioTracker.getWidth(),
      audioTracker.getHeight()
    };
  }

  public void updateAudioTracker(float durationSec, String filename, float receivedPercentage) {
    try {
      Slider audioTracker = cp5.get(Slider.class, "audio_tracker");
      if (audioTracker == null) return;

      // Update filename label if changed
      if (filename.length() > 0) {
        fileName.setText("AUDIO_FILE: " + filename);
      } else {
        fileName.setText("AUDIO_FILE:");
      }

      // Update tracker position
      if (durationSec > 0) {
        audioTracker.setRange(0, 100);
        float clampedPercentage = constrain(receivedPercentage, 0, 100);
        audioTracker.setValue(clampedPercentage);
      } else {
        audioTracker.setRange(0, 100);
        audioTracker.setValue(0);
      }
    }
    catch (Exception e) {
      println("Error updating audio tracker: " + e.getMessage());
    }
  }

  public void syncPlayerToggle(String state) {
    boolean shouldBeActive = state.equals("playing") || state.equals("paused");
    boolean currentlyActive = cp5.get(Toggle.class, "player_toggle").getBooleanValue();

    if (shouldBeActive && !currentlyActive) {
      cp5.get(Toggle.class, "player_toggle").setValue(true);
    } else if (!shouldBeActive && currentlyActive) {
      cp5.get(Toggle.class, "player_toggle").setValue(false);
    }
  }

  public void syncSessionToggle(String state) {
    boolean shouldBeActive = state.equals("playing");
    boolean currentlyActive = cp5.get(Toggle.class, "session_toggle").getBooleanValue();

    if (shouldBeActive && !currentlyActive) {
      cp5.get(Toggle.class, "session_toggle").setValue(true);
    } else if (!shouldBeActive && currentlyActive) {
      cp5.get(Toggle.class, "session_toggle").setValue(false);
    }
  }

  public void handleLoopEnabledChange(JSONObject json) {
    try {
      if (json.hasKey("loop_enabled")) {
        boolean loopEnabled = json.getBoolean("loop_enabled");
        boolean currentlyEnabled = cp5.get(Toggle.class, "loop_toggle").getBooleanValue();

        if (loopEnabled && !currentlyEnabled) {
          cp5.get(Toggle.class, "loop_toggle").setValue(true);
        } else if (!loopEnabled && currentlyEnabled) {
          cp5.get(Toggle.class, "loop_toggle").setValue(false);
        }
      }
    }
    catch (Exception ex) {
      println("Error parsing loop_enabled: " + ex.getMessage());
    }
  }

  public void handleVolumeChange(JSONObject json) {
    try {
      if (json.hasKey("volume")) {
        float newVolume = json.getFloat("volume");
        float currentVolume = cp5.get(Slider.class, "volume_slider").getValue();

        if (abs(newVolume - currentVolume) > 0.01f) {
          cp5.get(Slider.class, "volume_slider").setValue(newVolume);
        }
      }
    }
    catch (Exception ex) {
      println("Error parsing volume: " + ex.getMessage());
    }
  }

  public void onChannelToggle(boolean _flag) {
    if (!mqttManager.isConnected()) return;

    // Collect all 16 toggle states
    StringBuilder channelMask = new StringBuilder("[");
    for (int i = 1; i <= 16; i++) {
      String toggleName = "ch_" + i;
      boolean isEnabled = cp5.get(Toggle.class, toggleName).getBooleanValue();

      channelMask.append(isEnabled ? "1" : "0");

      if (i < 16) {
        channelMask.append(",");
      }
    }
    channelMask.append("]");

    // Send via MQTT
    String payload = channelMask.toString();
    mqttManager.publishCommand("channel_mask", payload);
    println("Sent channel mask: " + payload);
  }

  public void handlePlayerOffline() {
    cp5.get(Toggle.class, "player_toggle").setValue(false);
    cp5.get(Toggle.class, "session_toggle").setValue(false);
    cp5.get(Toggle.class, "loop_toggle").setValue(false);
    cp5.get(Slider.class, "audio_tracker").setValue(0);
    fileName.setText("AUDIO_FILE:");
  }

  public void handlePlayerOnline() {
    // Handle player coming online if needed
  }

  public void resetMqttToggle() {
    cp5.get(Toggle.class, "mqtt_toggle").setValue(false);
  }

  public void setMqttToggleValue(boolean value) {
    cp5.get(Toggle.class, "mqtt_toggle").setValue(value);
  }
}
