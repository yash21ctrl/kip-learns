import React, { useState, useEffect } from 'react';

// Random Reset Mission Pool
const MISSION_POOL = [
  {
    type: 'breathing',
    title: 'Breathing-Beat Reset',
    prompt: 'Follow Kip’s rhythm: Breathe in for 4 seconds, hold, then breathe out slowly.',
    duration: 10
  },
  {
    type: 'physical',
    title: 'Quick Body Reset',
    prompt: 'Stand up, stretch your arms high up to the sky, and do 3 gentle shoulder rolls!',
    duration: 8
  },
  {
    type: 'silly',
    title: 'Silly Question Time',
    prompt: 'If a cat could talk, what would its favorite subject in school be?',
    options: ['Meow-thematics', 'Purr-fessional History', 'Lunch Time'],
    duration: 0
  },
  {
    type: 'imagination',
    title: 'Brain Vacation',
    prompt: 'Close your eyes for 5 seconds and imagine you are floating peacefully on a soft cloud.',
    duration: 5
  }
];

export default function KipMentor({ 
  frustrationLevel = 'low', 
  triggerResetMission = false, 
  onResetComplete 
}) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [kipReasoning, setKipReasoning] = useState('');
  const [loadingReasoning, setLoadingReasoning] = useState(false);
  const [activeMission, setActiveMission] = useState(null);
  const [missionTimer, setMissionTimer] = useState(0);
  const [missionFinished, setMissionFinished] = useState(false);

  // 1. Map Frustration Level to Kip's 4 States
  const getKipState = () => {
    switch (frustrationLevel) {
      case 'medium':
        return {
          emoji: '🤔',
          label: 'Curious & Attentive',
          color: 'border-amber-400 bg-amber-500/20 text-amber-300',
          speech: "I'm leaning in! Taking a closer look at how we're doing."
        };
      case 'high':
        return {
          emoji: '😣',
          label: 'Noticed Friction',
          color: 'border-rose-500 bg-rose-500/20 text-rose-300',
          speech: "I noticed things got a bit tricky. Let's take a deep breath together!"
        };
      case 'celebrating':
        return {
          emoji: '🎉',
          label: 'Celebrating Flow!',
          color: 'border-emerald-400 bg-emerald-500/20 text-emerald-300 animate-bounce',
          speech: "Woohoo! You're in total hyperfocus right now!"
        };
      case 'low':
      default:
        return {
          emoji: '😌',
          label: 'Calm & Cheering',
          color: 'border-indigo-400 bg-indigo-500/20 text-indigo-300',
          speech: "Hey! I'm quietly cheering you on!"
        };
    }
  };

  const currentState = getKipState();

  // 2. Fetch Reasoning from Person A's /get-kip-reasoning endpoint on tap
  const handleTapKip = async () => {
    setIsDrawerOpen(!isDrawerOpen);
    if (!isDrawerOpen) {
      setLoadingReasoning(true);
      try {
        const response = await fetch('/get-kip-reasoning');
        const data = await response.json();
        setKipReasoning(data.reasoning || "Kip noticed hesitation spikes and backspaces, so we adjusted the pace gently.");
      } catch (err) {
        // Fallback demo reasoning if backend isn't connected yet
        setKipReasoning(`[Demo Logic]: Frustration score calculated as '${frustrationLevel}'. Hesitation threshold met. Decreasing option complexity and offering visual scaffolding.`);
      } finally {
        setLoadingReasoning(false);
      }
    }
  };

  // 3. Trigger Reset Mission takeover when backend signals trigger_reset_mission: true
  useEffect(() => {
    if (triggerResetMission && !activeMission) {
      const randomMission = MISSION_POOL[Math.floor(Math.random() * MISSION_POOL.length)];
      setActiveMission(randomMission);
      setMissionTimer(randomMission.duration);
      setMissionFinished(false);
    }
  }, [triggerResetMission]);

  // Countdown timer for reset mission
  useEffect(() => {
    let interval = null;
    if (activeMission && missionTimer > 0) {
      interval = setInterval(() => {
        setMissionTimer((prev) => prev - 1);
      }, 1000);
    } else if (activeMission && missionTimer === 0 && activeMission.type !== 'silly') {
      setMissionFinished(true);
    }
    return () => clearInterval(interval);
  }, [activeMission, missionTimer]);

  const handleFinishMission = () => {
    setActiveMission(null);
    setMissionFinished(false);
    if (onResetComplete) onResetComplete();
  };

  return (
    <div className="relative font-sans">
      {/* KIP COMPONENT CARD */}
      <div 
        onClick={handleTapKip}
        className={`cursor-pointer border p-3 rounded-xl transition-all flex items-center gap-3 shadow-lg ${currentState.color}`}
        title="Tap Kip to reveal AI reasoning (Demo Mode)"
      >
        <div className="w-12 h-12 rounded-full border border-current flex items-center justify-center text-2xl shadow-inner">
          {currentState.emoji}
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-white text-sm">Kip</span>
            <span className="text-[10px] bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700 text-slate-300">Tap me 👆</span>
          </div>
          <p className="text-xs font-medium">{currentState.label}</p>
        </div>
      </div>

      {/* TAP-TO-EXPAND REASONING DRAWER (Phase 2 Demo Mode) */}
      {isDrawerOpen && (
        <div className="mt-2 p-3 bg-slate-900 border border-indigo-500/50 rounded-xl shadow-2xl text-xs text-slate-200 animate-fadeIn">
          <div className="flex justify-between items-center mb-1 text-indigo-400 font-bold border-b border-slate-800 pb-1">
            <span>🧠 Kip's Internal Reasoning (Person A API)</span>
            <button onClick={() => setIsDrawerOpen(false)} className="text-slate-400 hover:text-white">✕</button>
          </div>
          {loadingReasoning ? (
            <p className="italic text-slate-400 py-2">Asking Kip's brain...</p>
          ) : (
            <p className="font-mono text-[11px] leading-relaxed text-slate-300 py-1">{kipReasoning}</p>
          )}
        </div>
      )}

      {/* RESET MISSION TAKEOVER MODAL (Phase 3) */}
      {activeMission && (
        <div className="fixed inset-0 bg-slate-950/90 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border-2 border-indigo-500/80 rounded-2xl p-6 max-w-md w-full shadow-2xl text-center flex flex-col items-center">
            
            {!missionFinished ? (
              <>
                <div className="text-5xl mb-3 animate-bounce">🧘</div>
                <h3 className="text-xl font-bold text-white mb-2">{activeMission.title}</h3>
                <p className="text-sm text-slate-300 mb-6 leading-relaxed">{activeMission.prompt}</p>

                {activeMission.type === 'silly' && (
                  <div className="w-full space-y-2 mb-4">
                    {activeMission.options.map((opt, i) => (
                      <button 
                        key={i} 
                        onClick={() => setMissionFinished(true)}
                        className="w-full bg-slate-800 hover:bg-indigo-600 border border-slate-700 text-slate-200 py-2 rounded-lg text-xs font-semibold transition-colors"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}

                {activeMission.duration > 0 && (
                  <div className="w-20 h-20 rounded-full border-4 border-indigo-500/30 border-t-indigo-400 flex items-center justify-center mb-4 animate-spin">
                    <span className="text-xl font-bold text-indigo-300 animate-none">{missionTimer}s</span>
                  </div>
                )}
              </>
            ) : (
              /* Kip Warm Reaction Phase */
              <div className="space-y-4">
                <div className="text-5xl">😌✨</div>
                <h3 className="text-xl font-bold text-emerald-400">Nice! Feeling refreshed?</h3>
                <p className="text-xs text-slate-300">Kip has adjusted the pacing. Let's hop back in when you're ready!</p>
                <button
                  onClick={handleFinishMission}
                  className="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-3 rounded-xl font-bold text-sm transition-all shadow-lg shadow-indigo-600/30"
                >
                  Resume Learning →
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
