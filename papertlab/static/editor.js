// editor.js

window.Editor = ({ file, content, onClose, onSave }) => {
    const editorRef = React.useRef(null);
    const [editorInstance, setEditorInstance] = React.useState(null);

    React.useEffect(() => {
        if (editorRef.current) {
            const editor = CodeMirror.fromTextArea(editorRef.current, {
                lineNumbers: true,
                mode: getLanguageMode(file),
                theme: 'monokai',
                autoCloseBrackets: true,
                matchBrackets: true,
                indentUnit: 4,
                tabSize: 4,
                indentWithTabs: false,
                foldGutter: true,
                gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter'],
                extraKeys: {
                    'Ctrl-/': 'toggleComment',
                    'Cmd-/': 'toggleComment',
                    'Ctrl-F': 'findPersistent',
                    'Cmd-F': 'findPersistent',
                    'Ctrl-H': 'replace',
                    'Cmd-Option-F': 'replace'
                },
                lint: true,
                styleActiveLine: true,
                hintOptions: {
                    completeSingle: false
                }
            });

            editor.setValue(content);
            editor.setSize('100%', '100%');

            setEditorInstance(editor);

            // Refresh the editor after a short delay to ensure proper sizing
            setTimeout(() => editor.refresh(), 100);

            return () => {
                editor.toTextArea();
            };
        }
    }, [file, content]);

    const getLanguageMode = (filename) => {
        const extension = filename.split('.').pop().toLowerCase();
        switch (extension) {
            case 'js': return 'javascript';
            case 'py': return 'python';
            case 'html': return 'htmlmixed';
            case 'css': return 'css';
            default: return 'javascript';
        }
    };

    const handleClose = () => {
        if (editorInstance) {
            const currentContent = editorInstance.getValue();
            onSave(currentContent);
        }
        onClose();
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-1 z-50">
            <div className="bg-gray-800 p-2 rounded-lg w-11/12 h-5/6 flex flex-col overflow-hidden">
                <div className="flex justify-between items-center p-1 border-b border-gray-700">
                    <h2 className="text-xl font-bold text-green-400">{file}</h2>
                    <div>
                        
                        <button
                            onClick={handleClose}
                            className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
                        >
                            Close
                        </button>
                    </div>
                </div>
                <div className="flex-grow overflow-hidden">
                    <textarea ref={editorRef} defaultValue={content} className="h-full w-full" />
                </div>
            </div>
        </div>
    );
};
