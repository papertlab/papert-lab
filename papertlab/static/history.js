const History = () => {
    const [chatHistory, setChatHistory] = React.useState([]);

    React.useEffect(() => {
        const fetchChatHistory = async () => {
            try {
                const response = await fetch('/api/chat_history');
                const data = await response.json();
                setChatHistory(data.history);
            } catch (error) {
                console.error('Error fetching chat history:', error);
            }
        };

        fetchChatHistory();
    }, []);

    return (
        <div className="container mx-auto p-4">
            <h1 className="text-2xl font-bold mb-4">Chat History</h1>
            {chatHistory.length > 0 ? (
                <ul className="space-y-4">
                    {chatHistory.map((chat, index) => (
                        <li key={index} className="border border-green-700 rounded p-4">
                            <p className="font-bold mb-2">Date: {new Date(chat.timestamp).toLocaleString()}</p>
                            <p className="whitespace-pre-wrap">{chat.content}</p>
                        </li>
                    ))}
                </ul>
            ) : (
                <p>No chat history available.</p>
            )}
        </div>
    );
};

ReactDOM.render(<History />, document.getElementById('root'));
