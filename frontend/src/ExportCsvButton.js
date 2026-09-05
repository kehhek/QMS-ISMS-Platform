import React, { useState } from 'react'
import { downloadFile } from './api'

export default function ExportCsvButton({ token, path, filename }) {
  const [error, setError] = useState(null)

  const click = () => {
    setError(null)
    downloadFile(`${path}export-csv/`, token, filename || 'export.csv').catch((err) => setError(err.message))
  }

  return (
    <>
      <button type="button" onClick={click}>Export CSV</button>
      {error && <span className="error-text" style={{ marginLeft: 8 }}>{error}</span>}
    </>
  )
}
