import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'
import ExportCsvButton from './ExportCsvButton'

function VideoPlayer({ video, token, onProgress }) {
  const [videoUrl, setVideoUrl] = useState(null)
  const [error, setError] = useState(null)
  const startedRef = React.useRef(false)

  useEffect(() => {
    let objectUrl = null
    // Blob-fetch-then-objectURL, same authenticated-download pattern as
    // every other file in this app (Document/Evidence) — a plain <video
    // src> can't carry an Authorization header, so this is the only way
    // to keep the file behind real auth rather than a public /media/ URL.
    // Trade-off: the whole file loads before playback starts (no
    // progressive streaming/seeking-ahead) — acceptable for a short
    // monthly awareness video.
    fetch(video.file, { headers: { Authorization: `Token ${token}` } })
      .then((r) => {
        if (!r.ok) throw new Error(`Could not load video (${r.status})`)
        return r.blob()
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        setVideoUrl(objectUrl)
      })
      .catch((err) => setError(err.message))
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [video.file, token])

  const markStart = () => {
    if (startedRef.current || !video.my_record_id) return
    startedRef.current = true
    apiFetch(`/training-records/${video.my_record_id}/start/`, token, { method: 'POST' })
      .then(onProgress)
      .catch(() => {})
  }

  const markComplete = () => {
    if (!video.my_record_id) return
    apiFetch(`/training-records/${video.my_record_id}/complete/`, token, { method: 'POST' })
      .then(onProgress)
      .catch(() => {})
  }

  if (error) return <p className="error-text">{error}</p>
  if (!videoUrl) return <p className="empty-state">Loading video…</p>

  return (
    <div>
      <video
        src={videoUrl}
        controls
        style={{ width: '100%', maxWidth: 640, display: 'block', marginBottom: 8, borderRadius: 8 }}
        onPlay={markStart}
        onEnded={markComplete}
      />
      {video.my_record_id && video.my_status !== 'completed' && (
        <button onClick={markComplete}>Mark as watched</button>
      )}
    </div>
  )
}

function TrainingVideosSection({ token }) {
  const [videos, setVideos] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ title: '', description: '', period: '' })
  const [file, setFile] = useState(null)
  const [playingId, setPlayingId] = useState(null)
  const [viewersId, setViewersId] = useState(null)
  const [viewers, setViewers] = useState(null)

  const load = () => {
    apiFetch('/training-videos/', token)
      .then((data) => setVideos(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line
  }, [])

  const upload = (e) => {
    e.preventDefault()
    if (!file) {
      setError('Choose a video file first.')
      return
    }
    const body = new FormData()
    body.append('title', form.title)
    body.append('description', form.description)
    body.append('period', form.period)
    body.append('file', file)
    apiFetch('/training-videos/', token, { method: 'POST', body })
      .then(() => {
        setForm({ title: '', description: '', period: '' })
        setFile(null)
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const publish = (video) => {
    apiFetch(`/training-videos/${video.id}/publish/`, token, { method: 'POST' })
      .then((data) => {
        setError(null)
        load()
        // eslint-disable-next-line no-alert
        window.alert(`Pushed to ${data.assigned_count} member(s) (${data.already_assigned_count} already had it).`)
      })
      .catch((err) => setError(err.message))
  }

  const loadViewers = (video) => {
    if (viewersId === video.id) {
      setViewersId(null)
      return
    }
    setViewersId(video.id)
    apiFetch(`/training-records/?video=${video.id}`, token)
      .then((data) => setViewers(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  return (
    <div style={{ marginBottom: 24 }}>
      <h3 style={{ marginBottom: 8 }}>Training Videos</h3>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Upload this month's awareness video and click "Push to everyone" to assign it to every
        active member — each shows up on their own list to watch, with Pending/In progress/
        Completed tracked per person below.
      </p>

      {/* Shown to every member, same as every other admin-gated form in
          this console (e.g. Assets' edit, Documents' status changes) —
          the backend (TrainingVideoViewSet) is the actual enforcement
          point and returns a clear, readable error if a non-admin/
          auditor submits this. */}
      <form onSubmit={upload} className="toolbar" style={{ flexWrap: 'wrap', marginBottom: 16 }}>
        <input
          placeholder="Title (e.g. September 2026 Security Awareness)"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          style={{ width: 280 }}
          required
        />
        <input
          placeholder="Period (e.g. September 2026)"
          value={form.period}
          onChange={(e) => setForm({ ...form, period: e.target.value })}
          style={{ width: 160 }}
        />
        <input
          placeholder="Description (optional)"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          style={{ width: 220 }}
        />
        <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files[0])} />
        <button type="submit" className="btn-primary">Upload video</button>
      </form>

      {videos.length === 0 ? (
        <p className="empty-state">No training videos yet.</p>
      ) : (
        <div style={{ display: 'grid', gap: 12 }}>
          {videos.map((v) => (
            <div key={v.id} className="workflow-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                <div>
                  <strong>{v.title}</strong>
                  {v.period && <span className="badge badge-neutral" style={{ marginLeft: 8 }}>{v.period}</span>}
                  {v.description && <p className="panel-hint" style={{ margin: '4px 0 0' }}>{v.description}</p>}
                </div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  {v.my_status && <StatusBadge value={v.my_status} />}
                  <button onClick={() => setPlayingId(playingId === v.id ? null : v.id)}>
                    {playingId === v.id ? 'Hide' : 'Watch'}
                  </button>
                  <button onClick={() => publish(v)}>Push to everyone</button>
                  <button onClick={() => loadViewers(v)}>
                    {viewersId === v.id ? 'Hide viewers' : 'View viewers'}
                  </button>
                </div>
              </div>

              <div className="stat-row" style={{ marginTop: 10 }}>
                <div className="stat-tile stat-tile-accent-neutral">
                  <div className="stat-tile-value">{v.pending_count}</div>
                  <div className="stat-tile-label"><StatusBadge value="assigned" /></div>
                </div>
                <div className="stat-tile stat-tile-accent-warning">
                  <div className="stat-tile-value">{v.in_progress_count}</div>
                  <div className="stat-tile-label"><StatusBadge value="in_progress" /></div>
                </div>
                <div className="stat-tile stat-tile-accent-success">
                  <div className="stat-tile-value">{v.completed_count}</div>
                  <div className="stat-tile-label"><StatusBadge value="completed" /></div>
                </div>
              </div>

              {playingId === v.id && (
                <div style={{ marginTop: 12 }}>
                  <VideoPlayer video={v} token={token} onProgress={load} />
                </div>
              )}

              {viewersId === v.id && (
                <div style={{ marginTop: 12, overflowX: 'auto' }}>
                  {viewers === null ? (
                    <p className="empty-state">Loading…</p>
                  ) : (
                    <table>
                      <thead>
                        <tr>
                          <th>Member</th>
                          <th>Status</th>
                          <th>Due</th>
                          <th>Completed</th>
                        </tr>
                      </thead>
                      <tbody>
                        {viewers.map((r) => (
                          <tr key={r.id}>
                            <td>{r.username}</td>
                            <td><StatusBadge value={r.status} /></td>
                            <td>{r.due_date || '—'}</td>
                            <td>{r.completed_date || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function SecurityAwarenessPanel({ token }) {
  const [records, setRecords] = useState([])
  const [members, setMembers] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ user: '', title: '', due_date: '' })

  const load = () => {
    apiFetch('/training-records/', token)
      .then((data) => setRecords(unwrapList(data)))
      .catch((err) => setError(err.message))
    apiFetch('/tenant/members/', token)
      .then((data) => {
        const list = unwrapList(data)
        setMembers(list)
        if (list.length && !form.user) setForm((f) => ({ ...f, user: String(list[0].user) }))
      })
      .catch(() => setMembers([]))
  }

  useEffect(() => {
    if (!token) return
    load()
    // eslint-disable-next-line
  }, [token])

  const assign = (e) => {
    e.preventDefault()
    apiFetch('/training-records/', token, {
      method: 'POST',
      body: JSON.stringify({ ...form, user: Number(form.user) }),
    })
      .then(() => {
        setForm({ ...form, title: '', due_date: '' })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const complete = (record) => {
    apiFetch(`/training-records/${record.id}/complete/`, token, { method: 'POST' })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view security awareness training.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}

      <TrainingVideosSection token={token} />

      <h3 style={{ marginBottom: 8 }}>Training Assignments</h3>
      <p className="panel-hint">
        Security awareness training tracking (ISO 27001 A.6.3). Admins/auditors assign training;
        anyone can mark their own assignment complete. Rows created by "Push to everyone" above
        show their video's title here too.
      </p>

      <form onSubmit={assign} className="toolbar">
        <select value={form.user} onChange={(e) => setForm({ ...form, user: e.target.value })}>
          {members.map((m) => (
            <option key={m.id} value={m.user}>{m.username}</option>
          ))}
        </select>
        <input
          placeholder="Training title (e.g. Annual security awareness 2026)"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          style={{ width: 280 }}
          required
        />
        <input
          type="date"
          value={form.due_date}
          onChange={(e) => setForm({ ...form, due_date: e.target.value })}
        />
        <button type="submit" className="btn-primary">Assign Training</button>
        <ExportCsvButton token={token} path="/training-records/" filename="training-records.csv" />
      </form>

      {records.length === 0 ? (
        <p className="empty-state">No training records yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Trainee</th>
              <th>Title</th>
              <th>Video</th>
              <th>Status</th>
              <th>Due</th>
              <th>Completed</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.id}>
                <td>{r.username}</td>
                <td>{r.title}</td>
                <td>{r.video_title || '—'}</td>
                <td>
                  <StatusBadge value={r.status} />
                  {r.is_overdue && <span className="badge badge-danger" style={{ marginLeft: 6 }}>overdue</span>}
                </td>
                <td>{r.due_date || '—'}</td>
                <td>{r.completed_date || '—'}</td>
                <td>
                  {r.status !== 'completed' && (
                    <button onClick={() => complete(r)}>Mark complete</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
