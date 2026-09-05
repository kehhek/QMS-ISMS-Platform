import React, { useState } from 'react'
import { downloadFile } from './api'

// `query` (e.g. "category=policy"), not baked into `path`, since the
// export-csv action is itself a real URL segment appended after `path`
// — a query string folded into `path` would land in the wrong place
// ("/documents/?category=policy&export-csv/" instead of
// "/documents/export-csv/?category=policy").
export default function ExportCsvButton({ token, path, filename, query }) {
  const [error, setError] = useState(null)

  const click = () => {
    setError(null)
    const url = `${path}export-csv/${query ? `?${query}` : ''}`
    downloadFile(url, token, filename || 'export.csv').catch((err) => setError(err.message))
  }

  return (
    <>
      <button type="button" onClick={click}>Export CSV</button>
      {error && <span className="error-text" style={{ marginLeft: 8 }}>{error}</span>}
    </>
  )
}
