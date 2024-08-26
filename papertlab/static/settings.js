const Notification = ({ message, show }) => {
    if (!show) return null;

    return (
        <div className="fixed bottom-4 right-4 bg-green-700 text-white px-4 py-2 rounded shadow-lg">
            {message}
        </div>
    );
};

const APISettings = ({ openAiKey, setOpenAiKey, anthropicKey, setAnthropicKey, handleSave }) => (
    <div className="p-6">
        <h2 className="text-xl font-bold mb-4">API Keys</h2>
        <div className="space-y-4">
            <div>
                <label className="block text-sm font-medium mb-2">OpenAI API Key</label>
                <input
                    type="text"
                    value={openAiKey}
                    onChange={(e) => setOpenAiKey(e.target.value)}
                    className="w-full p-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-green-500"
                    placeholder="Enter your OpenAI API Key"
                />
            </div>
            <div>
                <label className="block text-sm font-medium mb-2">Anthropic API Key</label>
                <input
                    type="text"
                    value={anthropicKey}
                    onChange={(e) => setAnthropicKey(e.target.value)}
                    className="w-full p-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-green-500"
                    placeholder="Enter your Anthropic API Key"
                />
            </div>
            <button
                onClick={handleSave}
                className="bg-green-700 text-black px-4 py-2 rounded hover:bg-green-600"
            >
                Save
            </button>
        </div>
    </div>
);

const UsageReport = () => {
    const [usageData, setUsageData] = React.useState([]);
    const [currentPage, setCurrentPage] = React.useState(1);
    const [totalPages, setTotalPages] = React.useState(0);
    const [isLoading, setIsLoading] = React.useState(true);
    const [error, setError] = React.useState(null);
    const itemsPerPage = 10;

    React.useEffect(() => {
        fetchUsageData(currentPage);
    }, [currentPage]);

    const fetchUsageData = async (page) => {
        setIsLoading(true);
        try {
            const response = await fetch(`/api/usage?page=${page}&per_page=${itemsPerPage}`);
            if (!response.ok) {
                throw new Error('Failed to fetch usage data');
            }
            const data = await response.json();
            setUsageData(data.usage);
            setTotalPages(Math.ceil(data.total / itemsPerPage));
            setIsLoading(false);
        } catch (error) {
            console.error('Error fetching usage data:', error);
            setError('Failed to load usage data. Please try again.');
            setIsLoading(false);
        }
    };

    const handlePageChange = (newPage) => {
        setCurrentPage(newPage);
    };

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-4">Usage Report</h1>
            {isLoading ? (
                <p>Loading usage data...</p>
            ) : error ? (
                <p className="text-red-500">{error}</p>
            ) : (
                <>
                    <div className="overflow-x-auto">
                        <table className="w-full border-collapse border border-green-800 mb-4">
                            <thead>
                                <tr className="bg-green-900">
                                    <th className="border border-green-800 p-2">Date</th>
                                    <th className="border border-green-800 p-2">Project</th>
                                    <th className="border border-green-800 p-2">Model</th>
                                    <th className="border border-green-800 p-2">Input Tokens</th>
                                    <th className="border border-green-800 p-2">Output Tokens</th>
                                    <th className="border border-green-800 p-2">Cost</th>
                                </tr>
                            </thead>
                            <tbody>
                                {usageData.map((item, index) => (
                                    <tr key={index} className={index % 2 === 0 ? "bg-green-800 bg-opacity-25" : ""}>
                                        <td className="border border-green-800 p-2">{new Date(item.datetime).toLocaleString()}</td>
                                        <td className="border border-green-800 p-2">{item.project_id}</td>
                                        <td className="border border-green-800 p-2">{item.model}</td>
                                        <td className="border border-green-800 p-2">{item.input_token}</td>
                                        <td className="border border-green-800 p-2">{item.output_token}</td>
                                        <td className="border border-green-800 p-2">${item.cost.toFixed(4)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <div className="flex justify-center items-center space-x-2">
                        <button
                            onClick={() => handlePageChange(currentPage - 1)}
                            disabled={currentPage === 1}
                            className="bg-green-700 text-black px-4 py-2 rounded disabled:opacity-50"
                        >
                            <i className="fas fa-chevron-left mr-2"></i>
                            Previous
                        </button>
                        <span>{currentPage} of {totalPages}</span>
                        <button
                            onClick={() => handlePageChange(currentPage + 1)}
                            disabled={currentPage === totalPages}
                            className="bg-green-700 text-black px-4 py-2 rounded disabled:opacity-50"
                        >
                            Next
                            <i className="fas fa-chevron-right ml-2"></i>
                        </button>
                    </div>
                </>
            )}
        </div>
    );
};

const ConfigSettings = ({ autoCommit, setAutoCommit, handleSave }) => (
    <div className="p-6">
        <h2 className="text-xl font-bold mb-4">Git Configuration</h2>
        <div className="space-y-4">
            <div className="flex items-center">
                <input
                    type="checkbox"
                    id="autoCommit"
                    checked={autoCommit}
                    onChange={(e) => setAutoCommit(e.target.checked)}
                    className="mr-2"
                />
                <label htmlFor="autoCommit" className="text-sm font-medium">
                    Enable Auto Commit
                </label>
            </div>
            <button
                onClick={handleSave}
                className="bg-green-700 text-black px-4 py-2 rounded hover:bg-green-600"
            >
                Save
            </button>
        </div>
    </div>
);


const Settings = () => {
    const [openAiKey, setOpenAiKey] = React.useState('');
    const [anthropicKey, setAnthropicKey] = React.useState('');
    const [currentView, setCurrentView] = React.useState('api');
    const [autoCommit, setAutoCommit] = React.useState(true);
    const [currentConfigView, setCurrentConfigView] = React.useState('git');
    const [notification, setNotification] = React.useState({ show: false, message: '' });

    React.useEffect(() => {
        const fetchApiKeys = async () => {
            try {
                const response = await fetch('/api/get_api_keys');
                const data = await response.json();
                setOpenAiKey(data.openai_api_key);
                setAnthropicKey(data.anthropic_api_key);
            } catch (error) {
                console.error('Error fetching API keys:', error);
            }
        };

        const fetchAutoCommitStatus = async () => {
            try {
                const response = await fetch('/api/get_auto_commit_status');
                const data = await response.json();
                setAutoCommit(data.auto_commit);
            } catch (error) {
                console.error('Error fetching auto commit status:', error);
            }
        };

        fetchApiKeys();
        fetchAutoCommitStatus();
    }, []);

    const showNotification = (message) => {
        setNotification({ show: true, message });
        setTimeout(() => {
            setNotification({ show: false, message: '' });
        }, 3000);
    };


    const handleSave = async () => {
        try {
            const response = await fetch('/api/set_api_key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ openai_key: openAiKey, anthropic_key: anthropicKey })
            });
            const data = await response.json();
            if (data.success) {
                showNotification('API keys saved successfully!');
            } else {
                throw new Error('Failed to save API keys');
            }
        } catch (error) {
            console.error('Error saving API keys:', error);
            alert('Failed to save API keys. Please try again.');
        }
    };

    const handleAutoCommitSave = async () => {
        try {
            const response = await fetch('/api/save_auto_commit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ auto_commit: autoCommit })
            });
            const data = await response.json();
            if (data.success) {
                showNotification('Auto commit setting saved successfully!');
            } else {
                throw new Error('Failed to save auto commit setting');
            }
        } catch (error) {
            console.error('Error saving auto commit setting:', error);
        }
    };

    return (
        <div className="flex h-screen">
            {/* Left Sidebar */}
            <div className="w-1/4 bg-gray-900 p-4 flex flex-col justify-between">
                <div>
                    <h2 className="text-lg font-bold mb-4">Settings</h2>
                    <ul className="space-y-2">
                        <li
                            className={`cursor-pointer p-2 rounded ${currentView === 'api' ? 'bg-gray-800 text-green-400' : ''}`}
                            onClick={() => setCurrentView('api')}
                        >
                            API
                        </li>
                        <li
                            className={`cursor-pointer p-2 rounded ${currentView === 'usage' ? 'bg-gray-800 text-green-400' : ''}`}
                            onClick={() => setCurrentView('usage')}
                        >
                            Usage
                        </li>
                        <li
                            className={`cursor-pointer p-2 rounded ${currentView === 'config' ? 'bg-gray-800 text-green-400' : ''}`}
                            onClick={() => setCurrentView('config')}
                        >
                            Config
                        </li>
                    </ul>
                </div>
                <div className="text-sm text-gray-500 mt-auto">
                    © 2024 <a href="https://papert.in" target="_blank">papert.in</a>
                </div>
            </div>

            {/* Right Content Area */}
            <div className="flex-grow">
                {currentView === 'api' && (
                    <APISettings
                        openAiKey={openAiKey}
                        setOpenAiKey={setOpenAiKey}
                        anthropicKey={anthropicKey}
                        setAnthropicKey={setAnthropicKey}
                        handleSave={handleSave}
                    />
                )}
                {currentView === 'usage' && <UsageReport />}
                {currentView === 'config' && (
                    <ConfigSettings
                        autoCommit={autoCommit}
                        setAutoCommit={setAutoCommit}
                        handleSave={handleAutoCommitSave}
                    />
                )}
            </div>
            {/* Notification */}
            <Notification message={notification.message} show={notification.show} />
        </div>
    );
};

ReactDOM.render(<Settings />, document.getElementById('root'));
