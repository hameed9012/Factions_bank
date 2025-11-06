import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, LineElement, PointElement, LinearScale, Title, Tooltip, Legend, CategoryScale } from 'chart.js';
import { format, formatDistanceToNow } from 'date-fns';
import { TrendingUp, Users, DollarSign, Clock, Trophy, Search, ChevronRight, Activity, ChevronLeft, ChevronDown } from 'lucide-react';
ChartJS.register(LineElement, PointElement, LinearScale, Title, Tooltip, Legend, CategoryScale);

// FIX: Set API to use local host/port explicitly, relying on Flask's new CORS setup.
const API = process.env.REACT_APP_API_URL || 'http://localhost:8085';

// --- NEW COMPONENT: Pagination Controls ---
const PaginationControls = ({ offset, limit, setOffset, totalCount }) => {
  const isPreviousDisabled = offset === 0;
  const isNextDisabled = offset + limit >= totalCount;
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(totalCount / limit);

  return (
    <div className="flex items-center justify-between mt-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Showing {Math.min(offset + 1, totalCount)} to {Math.min(offset + limit, totalCount)} of {totalCount} results
      </p>
      <div className="flex items-center space-x-2">
        <button
          onClick={() => setOffset(prev => Math.max(0, prev - limit))}
          disabled={isPreviousDisabled}
          className="p-2 border rounded-full disabled:opacity-50 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700 transition"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="text-sm font-medium text-slate-800 dark:text-slate-200">
          Page {currentPage} of {totalPages}
        </span>
        <button
          onClick={() => setOffset(prev => prev + limit)}
          disabled={isNextDisabled}
          className="p-2 border rounded-full disabled:opacity-50 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700 transition"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
// ------------------------------------------

// Horse SVG Component
const HorseIcon = ({ className = "w-16 h-16", running = false }) => (
  <svg 
    className={`${className} ${running ? 'animate-bounce' : ''}`}
    viewBox="0 0 64 64" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2"
  >
    <path d="M 20 30 L 25 20 L 35 18 L 40 22 L 42 30" strokeLinecap="round"/>
    <circle cx="35" cy="20" r="3" fill="currentColor"/>
    <path d="M 20 30 L 18 45 M 25 30 L 27 45" strokeLinecap="round"/>
    <path d="M 42 30 L 40 45 M 37 30 L 39 45" strokeLinecap="round"/>
    <path d="M 15 15 Q 20 10 25 15" strokeLinecap="round"/>
  </svg>
);
// Race Track Component with Animations
const RaceTrack = ({ race, compact = false }) => {
  const [animationProgress, setAnimationProgress] = useState(0);
useEffect(() => {
    if (race.status === 'live') {
      const interval = setInterval(() => {
        setAnimationProgress(prev => (prev + 1) % 100);
      }, 50);
      return () => clearInterval(interval);
    } else if (race.status === 'finished') {
      setAnimationProgress(100);
    }
  }, [race.status]);
const getPosition = (index) => {
    if (race.status === 'scheduled') return 0;
if (race.status === 'finished') {
      const jockey = race.jockeys[index];
      if (jockey === race.winner1) return 100;
if (jockey === race.winner2) return 95;
      if (jockey === race.winner3) return 90;
      return 85;
}
    return animationProgress + (index * 5) % 100;
  };

  const trackHeight = compact ?
'h-24' : 'h-40';

  return (
    <div className="relative w-full bg-gradient-to-r from-green-100 via-green-50 to-green-100 dark:from-green-900 dark:via-green-800 dark:to-green-900 rounded-xl overflow-hidden border-2 border-green-300 dark:border-green-700">
      {/* Finish Line */}
      <div className="absolute right-0 top-0 bottom-0 w-4 bg-gradient-to-r from-transparent via-yellow-400 to-yellow-500 opacity-50"></div>
      
      {/* Lanes */}
      <div className={`relative ${trackHeight} flex flex-col justify-around py-2`}>
        {race.jockeys?.map((jockey, idx) => {
          const position = getPosition(idx);
   
        const isWinner = race.status === 'finished' && 
                          [race.winner1, race.winner2, race.winner3].includes(jockey);
          
          return (
            <div key={idx} className="relative h-10 border-b border-green-200 dark:border-green-700 last:border-0">
              <div 
   
              className="absolute top-1/2 -translate-y-1/2 transition-all duration-1000 ease-linear flex items-center gap-2"
                style={{ left: `${position}%` }}
              >
                <HorseIcon 
                  className={`w-8 h-8 ${isWinner ?
'text-yellow-500' : 'text-gray-700 dark:text-gray-300'}`}
                  running={race.status === 'live'}
                />
                {!compact && (
                  <span className={`text-xs font-bold whitespace-nowrap ${
                    isWinner 
? 'text-yellow-600 dark:text-yellow-400' : 'text-gray-600 dark:text-gray-400'
                  }`}>
                    {jockey}
                    {jockey === race.winner1 && ' 🥇'}
                    {jockey === race.winner2 && ' 🥈'}
       
              {jockey === race.winner3 && ' 🥉'}
                  </span>
                )}
              </div>
            </div>
          );
})}
      </div>
      
      {/* Status Banner */}
      {race.status === 'finished' && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="text-center">
            <Trophy className="w-16 h-16 text-yellow-400 mx-auto mb-2 animate-pulse" />
            <p className="text-2xl font-bold text-white">Race Complete!</p>
        
    </div>
        </div>
      )}
    </div>
  );
};

// Time Until Component
const TimeUntil = ({ date }) => {
  const [, setTick] = useState(0);
useEffect(() => {
    const interval = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(interval);
  }, []);
if (!date) return <span className="text-gray-500">Never</span>;
  
  const targetDate = new Date(date);
  const now = new Date();
// FIX: Swapped logic to display time since compound, not time until start.
if (targetDate > now) {
    return <span className="text-green-600 dark:text-green-400 font-medium">{formatDistanceToNow(targetDate, { addSuffix: true })}</span>;
}
  
  return (
    <span className="text-slate-600 dark:text-slate-400 font-medium">
      {formatDistanceToNow(targetDate, { addSuffix: false })} ago
    </span>
  );
};

// Main App Component
function App() {
  const [players, setPlayers] = useState([]);
  const [txns, setTxns] = useState([]);
  const [search, setSearch] = useState('');
  const [settings, setSettings] = useState({});
  const [history, setHistory] = useState([]);
  const [races, setRaces] = useState([]);
  const [selectedRace, setSelectedRace] = useState(null);
  const [view, setView] = useState('bank');
  const [loading, setLoading] = useState(true);
  
  // --- NEW STATE FOR PAGINATION ---
  const PLAYER_LIMIT = 15;
  const [playerTotal, setPlayerTotal] = useState(0); // Assuming the backend doesn't return total count currently
  const [playerOffset, setPlayerOffset] = useState(0);
  
  const TXN_LIMIT = 20;
  const [txnOffset, setTxnOffset] = useState(0);
  // --- END NEW STATE ---

useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
}, [search, view, playerOffset, txnOffset]); // Add pagination state to dependency array

const loadData = async () => {
    try {
      const requests = [
        axios.get(`${API}/api/settings`),
        axios.get(`${API}/api/interest/history`)
      ];
      
      const playerUrl = `${API}/api/players?q=${search}&limit=${PLAYER_LIMIT}&offset=${playerOffset}`;
      const txnUrl = `${API}/api/transactions?ign=${search}&limit=${TXN_LIMIT}&offset=${txnOffset}`;
      const raceUrl = `${API}/api/races`;


      if (view === 'bank') {
        requests.push(
          axios.get(playerUrl),
          axios.get(txnUrl),
          // Fetch all players for a proper total count (Less efficient, but necessary if API lacks count endpoint)
          axios.get(`${API}/api/players`) 
        );
      } else {
        requests.push(axios.get(raceUrl));
      }
      
      const responses = await Promise.all(requests);
      
      setSettings(responses[0].data);
      
      // FIX: Reverse history data here so map functions can display it correctly (latest data first)
      setHistory(responses[1].data.reverse()); 

      if (view === 'bank') {
        setPlayers(responses[2].data);
        setTxns(responses[3].data);
        // Set total count based on the request that fetches ALL players
        setPlayerTotal(responses[4]?.data?.length || 0);
      } else {
        setRaces(responses[2].data);
      }
      
      setLoading(false);
} catch (e) {
      console.error('Error loading data:', e);
      setLoading(false);
    }
  };
const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount || 0);
};

  const formatDate = (date) => {
    if (!date) return 'Never';
return format(new Date(date), 'MMM dd, yyyy HH:mm');
  };

  // Chart Data
  const chartData = {
    // FIX: Remove .reverse() here as it's now done during state setting
    labels: history.map(h => format(new Date(h.changed_at), 'MMM dd, HH:mm')),
    datasets: [
      {
        label: 'Normal Rate (%)',
        data: history.map(h => h.rate_normal_pct),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
        fill: 
true,
        yAxisID: 'y'
      },
      {
        label: 'Premium Rate (%)',
        data: history.map(h => h.rate_premium_pct),
        borderColor: 'rgb(245, 158, 11)',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        tension: 0.4,
        fill: true,
        yAxisID: 'y'
      },
 
      {
        label: 'Premium Min Balance ($)',
        data: history.map(h => h.premium_min_balance),
        borderColor: 'rgb(16, 185, 129)',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        tension: 0.4,
        fill: true,
        yAxisID: 'y1'
      }
    ]
  };
const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { font: { size: 11 }, padding: 10 }
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(0, 0, 0, 0.8)'
      
}
    },
    scales: {
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        title: { display: true, text: 'Rate (%)' },
        beginAtZero: true
      },
      y1: {
        type: 'linear',
        display: true,
  
        position: 'right',
        title: { display: true, text: 'Balance ($)' },
        grid: { drawOnChartArea: false },
        beginAtZero: true
      }
    },
    interaction: { mode: 'nearest', axis: 'x', intersect: false }
  };
if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-16 h-16 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-xl font-semibold text-gray-700 dark:text-gray-300">Loading Factions Bank...</p>
        </div>
      </div>
    );
}

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 text-slate-900 dark:text-slate-100">
      <div className="max-w-7xl mx-auto p-3 sm:p-6 lg:p-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <h1 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
            🏦 Factions Bank
          </h1>
     
          <div className="flex items-center gap-3 bg-white dark:bg-slate-800 px-4 py-2 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700">
            <DollarSign className="w-6 h-6 text-green-600" />
            <div>
              <p className="text-xs text-gray-500">Total Bank Debt</p>
              <p className="text-xl font-bold text-green-600">
                {formatCurrency(settings.total_bank_debt)}
    
            </p>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
          <div className="bg-white dark:bg-slate-800 p-4 sm:p-6 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 hover:shadow-xl transition-shadow">
            <div 
className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">Normal Rate</p>
                <p className="text-2xl sm:text-3xl font-bold text-blue-600">
                  {((settings.bank?.interest_rate_normal ||
0) * 100).toFixed(2)}%
                </p>
              </div>
              <TrendingUp className="w-8 h-8 sm:w-10 sm:h-10 text-blue-600" />
            </div>
          </div>
          
          <div className="bg-white dark:bg-slate-800 p-4 sm:p-6 rounded-xl 
shadow-lg border border-slate-200 dark:border-slate-700 hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">Premium Rate</p>
                <p className="text-2xl sm:text-3xl font-bold text-amber-600">
                  {((settings.bank?.interest_rate_premium || 0) * 100).toFixed(2)}%
   
              </p>
                <p className="text-xs text-slate-500">
                  ≥{formatCurrency(settings.bank?.premium_min_balance || 0)}
                </p>
              </div>
              <Trophy className="w-8 h-8 sm:w-10 sm:h-10 
text-amber-600" />
            </div>
          </div>
          
          <div className="bg-white dark:bg-slate-800 p-4 sm:p-6 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p 
className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">Active Players</p>
                <p className="text-2xl sm:text-3xl font-bold text-emerald-600">{playerTotal}</p>
              </div>
              <Users className="w-8 h-8 sm:w-10 sm:h-10 text-emerald-600" />
            </div>
          </div>
          
          
<div className="bg-white dark:bg-slate-800 p-4 sm:p-6 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">Payout Fee</p>
                <p className="text-2xl sm:text-3xl font-bold text-red-600">
                  {((settings.bank?.payout_fee_pct 
|| 0) * 100).toFixed(2)}%
                </p>
              </div>
              <Activity className="w-8 h-8 sm:w-10 sm:h-10 text-red-600" />
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
      
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2 border-b-2 border-slate-200 dark:border-slate-700">
          <button
            onClick={() => setView('bank')}
            className={`px-4 sm:px-6 py-2 sm:py-3 font-medium transition-all rounded-t-lg whitespace-nowrap flex items-center gap-2 ${
              view === 'bank'
                ?
'bg-white dark:bg-slate-800 text-blue-600 border-t-4 border-x-2 border-blue-600'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
            }`}
          >
            <DollarSign className="w-5 h-5" />
            Bank Dashboard
          </button>
          <button
     
            onClick={() => setView('races')}
            className={`px-4 sm:px-6 py-2 sm:py-3 font-medium transition-all rounded-t-lg whitespace-nowrap flex items-center gap-2 ${
              view === 'races'
                ?
'bg-white dark:bg-slate-800 text-purple-600 border-t-4 border-x-2 border-purple-600'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
            }`}
          >
            <HorseIcon className="w-5 h-5" />
            Imperial Races
          </button>
        </div>

       
        {/* Search Bar */}
        {view === 'bank' && (
          <div className="mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
        
                placeholder="Search player by name..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-3 rounded-xl border-2 border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
          
    </div>
          </div>
        )}

        {/* Content */}
        {view === 'bank' ?
(
          <div className="space-y-6">
            {/* Players Table */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-4 sm:p-6 border border-slate-200 dark:border-slate-700">
              <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Users className="w-6 h-6 text-blue-600" />
             
    Players ({playerTotal})
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b-2 border-slate-200 dark:border-slate-700">
         
                      <th className="text-left py-3 px-2 font-semibold text-sm">Player</th>
                      <th className="text-right py-3 px-2 font-semibold text-sm">Balance</th>
                      <th className="text-center py-3 px-2 font-semibold text-sm hidden sm:table-cell">Rate</th>
                      <th className="text-right py-3 px-2 
font-semibold text-sm hidden md:table-cell">Last Interest</th>
                    </tr>
                  </thead>
                  <tbody>
                    {players.map(p => (
                  
                      <tr key={p.ign} className="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                        <td className="py-3 px-2">
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br 
from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-xs sm:text-sm font-bold flex-shrink-0">
                              {p.ign[0].toUpperCase()}
                            </div>
                            <div>
    
                              <div className="font-medium text-sm sm:text-base">{p.ign}</div>
                              {p.is_premium ?
(
                                <span className="inline-block text-xs bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200 px-2 py-0.5 rounded-full">
                                  ⭐ Premium
                        
          </span>
                              ) : null}
                            </div>
                          </div>
      
                      </td>
                        <td className="text-right font-bold text-sm sm:text-lg whitespace-nowrap">
                          {formatCurrency(p.balance)}
                        </td>
   
                         <td className="text-center hidden sm:table-cell">
                          <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold ${
                            p.is_premium 
              
                            ?
'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                              : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                          }`}>
                            {((p.interest_rate || 0) * 100).toFixed(2)}%
     
                           </span>
                        </td>
                        <td className="text-right text-xs text-slate-600 dark:text-slate-400 hidden md:table-cell">
                         
                          <div className="flex items-center justify-end gap-1">
                            <Clock className="w-4 h-4" />
                            <TimeUntil date={p.last_compounded_at} />
                          </div>
        
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
        
              </div>
              <PaginationControls 
                offset={playerOffset} 
                limit={PLAYER_LIMIT} 
                setOffset={setPlayerOffset} 
                totalCount={playerTotal} 
              />
            </div>

            {/* Transactions */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-4 sm:p-6 border border-slate-200 dark:border-slate-700">
              <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Activity className="w-6 h-6 text-green-600" />
       
                Recent Transactions ({txns.length})
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b-2 border-slate-200 dark:border-slate-700">
  
                      <th className="text-left py-3 px-2 font-semibold text-sm">Player</th>
                      <th className="text-center py-3 px-2 font-semibold text-sm">Type</th>
                      <th className="text-right py-3 px-2 font-semibold text-sm">Amount</th>
                     
                      <th className="text-left py-3 px-2 font-semibold text-sm hidden lg:table-cell">Note</th>
                      <th className="text-right py-3 px-2 font-semibold text-sm hidden md:table-cell">Date</th>
                    </tr>
                  </thead>
                  <tbody>
       
              {txns.map(t => (
                      <tr key={t.id} className="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                        <td className="py-3 px-2 font-medium text-sm">{t.ign}</td>
                        <td className="text-center">
  
                          <span className={`px-2 sm:px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap ${
                            ['deposit', 'interest', 'horse_race_win'].includes(t.txn_type)
                              ?
'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                              : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                          }`}>
                            {t.txn_type.replace(/_/g, ' ').replace('horse race', '🐴')}
     
                           </span>
                        </td>
                        <td className={`text-right font-bold text-sm ${
                          parseFloat(t.effective_delta) 
>= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {parseFloat(t.effective_delta) >= 0 ?
'+' : ''}
                          {formatCurrency(Math.abs(parseFloat(t.effective_delta)))}
                        </td>
                        <td className="text-left text-xs text-slate-600 dark:text-slate-400 max-w-xs truncate hidden lg:table-cell">
                
                          {t.note ||
'-'}
                        </td>
                        <td className="text-right text-xs text-slate-500 whitespace-nowrap hidden md:table-cell">
                          {formatDate(t.created_at)}
                    
                      </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* NOTE: Total count for transactions is not exposed by the API yet, 
                     but pagination is implemented using the limit/offset structure */}
               <PaginationControls 
                offset={txnOffset} 
                limit={TXN_LIMIT} 
                setOffset={setTxnOffset} 
                totalCount={txns.length + txnOffset + (txns.length < TXN_LIMIT ? 0 : 1)}
              />
          </div>

            {/* Interest Rate History Graph */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-4 sm:p-6 border border-slate-200 dark:border-slate-700">
              <h3 className="text-xl font-bold mb-4">📈 Interest Rate History</h3>
              <div className="h-64 sm:h-80">
                <Line data={chartData} options={chartOptions} />
 
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Race Settings Info */}
            {settings.horse_race && (
              
<div className="bg-gradient-to-r from-purple-100 via-pink-100 to-yellow-100 dark:from-purple-900 dark:via-pink-900 dark:to-yellow-900 p-4 sm:p-6 rounded-2xl shadow-lg border-2 border-purple-300 dark:border-purple-700">
                <h3 className="text-2xl font-bold mb-3 flex items-center gap-2">
                  <Trophy className="w-8 h-8 text-yellow-600" />
                  Imperial Race Rules
                </h3>
      
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                  <div className="bg-white dark:bg-slate-800 p-3 rounded-lg">
                    <p className="text-xs text-gray-500">Entry Fee</p>
                    <p className="text-xl font-bold text-blue-600">{formatCurrency(settings.horse_race.entry_fee)}</p>
                
    </div>
                  <div className="bg-white dark:bg-slate-800 p-3 rounded-lg">
                    <p className="text-xs text-gray-500">Imperial Cut</p>
                    <p className="text-xl font-bold text-red-600">{settings.horse_race.imperial_cut}%</p>
                  </div>
            
              <div className="bg-white dark:bg-slate-800 p-3 rounded-lg">
                    <p className="text-xs text-gray-500">1st / 2nd / 3rd</p>
                    <p className="text-lg font-bold text-yellow-600">
                      {settings.horse_race.winner1_pct}% / {settings.horse_race.winner2_pct}% / {settings.horse_race.winner3_pct}%
               
            </p>
                  </div>
                </div>
                <div className="bg-white dark:bg-slate-800 p-4 rounded-lg">
                  <p className="text-sm whitespace-pre-line leading-relaxed">
                    
{settings.horse_race.rules?.replace(/\\n/g, '\n') || 'No rules set'}
                  </p>
                </div>
              </div>
            )}

            {/* Selected Race Detail */}
            {selectedRace && (
     
              <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-4 sm:p-6 border border-slate-200 dark:border-slate-700">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-2xl font-bold">{selectedRace.name} #{selectedRace.id}</h3>
                  <button
                    onClick={() => setSelectedRace(null)}
 
                    className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  >
                    ✕
                  </button>
                </div>
       
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                  <div>
                    <p className="text-xs text-gray-500">Prize Pool</p>
                    <p className="text-xl font-bold text-green-600">{formatCurrency(selectedRace.prize_pool)}</p>
                  </div>
    
                  <div>
                    <p className="text-xs text-gray-500">Jockeys</p>
                    <p className="text-xl font-bold text-purple-600">{selectedRace.jockey_count}</p>
                  </div>
                  <div>
     
                    <p className="text-xs text-gray-500">Status</p>
                    <span className={`inline-block px-3 py-1 rounded-full text-sm font-bold ${
                      selectedRace.status === 'live' ?
'bg-green-100 text-green-800' :
                      selectedRace.status === 'finished' ?
'bg-yellow-100 text-yellow-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {selectedRace.status.toUpperCase()}
                    </span>
             
              </div>
                  <div>
                    <p className="text-xs text-gray-500">Scheduled</p>
                    <p className="text-sm font-medium">
                      {selectedRace.status === 'scheduled' ?
(
                        <TimeUntil date={selectedRace.scheduled_at} />
                      ) : (
                        formatDate(selectedRace.scheduled_at)
                      )}
    
                    </p>
                  </div>
                </div>
                <RaceTrack race={selectedRace} />
              </div>
            )}

      
            {/* Races Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {races.length === 0 ?
(
                <div className="col-span-2 text-center py-12 bg-white dark:bg-slate-800 rounded-2xl shadow-lg">
                  <HorseIcon className="w-24 h-24 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
                  <p className="text-xl text-gray-500">No races scheduled yet</p>
                </div>
             
              ) : (
                races.map(race => (
                  <div
                    key={race.id}
                    onClick={() => setSelectedRace(race)}
                   
                    className="bg-white dark:bg-slate-800 p-4 sm:p-6 rounded-2xl shadow-lg border border-slate-200 dark:border-slate-700 hover:shadow-xl transition-all cursor-pointer hover:scale-[1.02]"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <h3 className="text-lg font-bold">{race.name} #{race.id}</h3>
                    
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        race.status === 'live' ?
'bg-green-100 text-green-800 animate-pulse' :
                        race.status === 'finished' ?
'bg-yellow-100 text-yellow-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {race.status.toUpperCase()}
                      </span>
     
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
                      <div>
                  
                        <p className="text-gray-500">Prize Pool</p>
                        <p className="font-bold text-green-600">{formatCurrency(race.prize_pool)}</p>
                      </div>
                      <div>
                      
                        <p className="text-gray-500">Jockeys</p>
                        <p className="font-bold text-purple-600">{race.jockey_count}</p>
                      </div>
                      <div className="col-span-2">
                        <p className="text-gray-500">Scheduled</p>
 
                        <p className="font-medium">
                          {race.status === 'scheduled' ?
(
                            <TimeUntil date={race.scheduled_at} />
                          ) : (
                            formatDate(race.scheduled_at)
              
                          )}
                        </p>
                      </div>
                    </div>

                    {/* Mini 
Race Track Preview */}
                    <RaceTrack race={race} compact={true} />

                    {/* Winners Display */}
                    {race.status === 'finished' && (
                      <div className="mt-4 pt-4 border-t border-gray-200 
dark:border-gray-700">
                        <p className="text-xs font-semibold text-gray-500 mb-2">Winners:</p>
                        <div className="flex flex-wrap gap-2">
                          {race.winner1 && (
                 
                            <span className="inline-flex items-center gap-1 px-3 py-1 bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded-full text-xs font-bold">
                              🥇 {race.winner1}
                            </span>
                  
                          )}
                          {race.winner2 && (
                            <span className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200 rounded-full text-xs font-bold">
                        
          🥈 {race.winner2}
                            </span>
                          )}
                          {race.winner3 && (
           
                            <span className="inline-flex items-center gap-1 px-3 py-1 bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200 rounded-full text-xs font-bold">
                              🥉 {race.winner3}
                            </span>
            
              )}
                        </div>
                      </div>
                    )}

                    
<div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                      <span>Click to view details</span>
                      <ChevronRight className="w-4 h-4" />
                    </div>
                  </div>
      
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;