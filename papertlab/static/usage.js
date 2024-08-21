const UsageReport = () => {
    const [usageData, setUsageData] = React.useState([]);
    const [currentPage, setCurrentPage] = React.useState(1);
    const [totalPages, setTotalPages] = React.useState(0);
    const [isLoading, setIsLoading] = React.useState(true);
    const [error, setError] = React.useState(null);
    const [showUserDropdown, setShowUserDropdown] = React.useState(false);
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
        <div className="bg-black min-h-screen">
            <nav className="bg-green-900 p-4 mb-4">
                <div className="container mx-auto flex justify-between items-center">
                    <a href="/" className="text-xl font-bold text-green-400">papert-lab</a>
                    <div className="relative">
                        <button
                            onClick={() => setShowUserDropdown(!showUserDropdown)}
                            className="bg-green-700 text-black px-2 sm:px-4 py-1 sm:py-2 rounded-full hover:bg-green-600 focus:outline-none"
                        >
                            <i className="fas fa-user"></i>
                        </button>
                        {showUserDropdown && (
                            <div className="absolute right-0 mt-2 w-48 bg-green-700 rounded-md shadow-lg py-1 z-10">
                                <a href="/usage" className="block px-4 py-2 text-sm text-black hover:bg-green-600">Usage Report</a>
                                <a href="/settings" className="block px-4 py-2 text-sm text-black hover:bg-green-600">Settings</a>
                                <a href="/history" className="block px-4 py-2 text-sm text-black hover:bg-green-600">History</a>
                            </div>
                        )}
                    </div>
                </div>
            </nav>
            <div className="container mx-auto p-4">
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
        </div>
    );
};

ReactDOM.render(<UsageReport />, document.getElementById('root'));
