/* ═══════════════════════════════════════════════════════ */
/*  C.Y.C.L.O.S. HUD — Web Audio API SFX Engine           */
/*  Procedural cinematic telemetry and interaction sounds  */
/* ═══════════════════════════════════════════════════════ */

/**
 * AudioSFX
 * ────────
 * Uses the native browser Web Audio API to synthesize UI sound effects
 * dynamically, preventing the need to load static MP3/WAV files.
 */
class AudioSFX {
    constructor() {
        this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        this.masterGain = this.ctx.createGain();
        this.masterGain.gain.value = 0.5;
        this.masterGain.connect(this.ctx.destination);
        this.initialized = false;

        // Background hum oscillators
        this.humOsc = null;
        this.humGain = null;
    }

    /**
     * Must be called after a user interaction to unlock the AudioContext
     */
    init() {
        if (this.initialized) return;
        if (this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
        this.initialized = true;
        this._startBackgroundHum();
        console.log('[AUDIO] Web Audio API Synthesizer Initialized.');
    }

    /**
     * Play a short futuristic "blip" for button hovers or data ticks
     */
    playBlip(freq = 800, type = 'sine', duration = 0.05, vol = 0.1) {
        if (!this.initialized) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = type;
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(freq * 0.5, this.ctx.currentTime + duration);

        gain.gain.setValueAtTime(vol, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + duration);

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.start();
        osc.stop(this.ctx.currentTime + duration);
    }

    /**
     * Play a cinematic low "thud" or "boom" for major state transitions
     */
    playBoom() {
        if (!this.initialized) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(150, this.ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 1.0);

        gain.gain.setValueAtTime(0.8, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 1.0);

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.start();
        osc.stop(this.ctx.currentTime + 1.0);
    }

    /**
     * Low continuous drone representing the physical cycloreactor
     */
    _startBackgroundHum() {
        this.humOsc = this.ctx.createOscillator();
        this.humGain = this.ctx.createGain();

        this.humOsc.type = 'triangle';
        this.humOsc.frequency.value = 55; // Low frequency hum

        this.humGain.gain.value = 0.05; // Very subtle

        this.humOsc.connect(this.humGain);
        this.humGain.connect(this.masterGain);

        this.humOsc.start();
    }

    /**
     * Update the hum pitch based on the physical reactor's pump frequency
     * @param {number} hz - Pump frequency (e.g. 20-60 Hz)
     */
    updateReactorHum(hz) {
        if (!this.initialized || !this.humOsc) return;
        // Map 0-60 Hz pump speed to audible 40-100 Hz hum
        const mappedFreq = 40 + (hz * 1.0);
        this.humOsc.frequency.setTargetAtTime(mappedFreq, this.ctx.currentTime, 0.5);
    }

    /**
     * Play an alert siren for biosecurity or PH shock events
     */
    playAlert() {
        if (!this.initialized) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'square';
        osc.frequency.setValueAtTime(400, this.ctx.currentTime);
        osc.frequency.linearRampToValueAtTime(600, this.ctx.currentTime + 0.2);
        osc.frequency.linearRampToValueAtTime(400, this.ctx.currentTime + 0.4);

        gain.gain.setValueAtTime(0.2, this.ctx.currentTime);
        gain.gain.linearRampToValueAtTime(0, this.ctx.currentTime + 0.4);

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.start();
        osc.stop(this.ctx.currentTime + 0.4);
    }
}

// Global instance
window.audioSFX = new AudioSFX();

// Auto-initialize on first user click anywhere on the document
document.addEventListener('click', () => {
    window.audioSFX.init();
}, { once: true });
