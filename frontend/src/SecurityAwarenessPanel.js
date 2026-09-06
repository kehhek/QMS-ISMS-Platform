import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'
import ExportCsvButton from './ExportCsvButton'

function VideoQuiz({ video, token, onDone }) {
  const [questions, setQuestions] = useState(null)
  const [answers, setAnswers] = useState({})
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    apiFetch(`/training-videos/${video.id}/quiz/`, token)
      .then((data) => setQuestions(unwrapList(data)))
      .catch((err) => setError(err.message))
    // eslint-disable-next-line
  }, [video.id])

  const submit = (e) => {
    e.preventDefault()
    if (Object.keys(answers).length !== questions.length) {
      setError('Answer every question first.')
      return
    }
    setSubmitting(true)
    setError(null)
    const orderedAnswers = questions.map((q) => answers[q.id])
    apiFetch(`/training-records/${video.my_record_id}/submit-quiz/`, token, {
      method: 'POST',
      body: JSON.stringify({ answers: orderedAnswers }),
    })
      .then((data) => {
        setResult(data)
        onDone()
      })
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  if (error && !questions) return <p className="error-text">{error}</p>
  if (!questions) return <p className="empty-state">Loading quiz…</p>

  if (result) {
    return (
      <div className="workflow-card" style={{ marginTop: 8 }}>
        <p className={result.passed ? 'success-text' : 'error-text'}>
          {result.passed
            ? `Passed — ${result.correct}/${result.total} correct (${result.quiz_score}%). Marked complete.`
            : `Not quite — ${result.correct}/${result.total} correct (${result.quiz_score}%, need ${video.pass_percent}% to pass). Rewatch and try again.`}
        </p>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="workflow-card" style={{ marginTop: 8 }}>
      <p className="panel-hint">
        Quick check — answer all {questions.length} question{questions.length === 1 ? '' : 's'} to mark this
        video complete ({video.pass_percent}% required to pass).
      </p>
      {error && <p className="error-text">{error}</p>}
      {questions.map((q, i) => (
        <div key={q.id} style={{ marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>{i + 1}. {q.text}</div>
          {q.options.map((opt, optIndex) => (
            <label key={optIndex} style={{ display: 'block', fontSize: 13, marginBottom: 2 }}>
              <input
                type="radio"
                name={`q-${q.id}`}
                checked={answers[q.id] === optIndex}
                onChange={() => setAnswers({ ...answers, [q.id]: optIndex })}
                style={{ marginRight: 6 }}
              />
              {opt}
            </label>
          ))}
        </div>
      ))}
      <button type="submit" className="btn-primary" disabled={submitting}>
        {submitting ? 'Submitting…' : 'Submit quiz'}
      </button>
    </form>
  )
}

function VideoPlayer({ video, token, onProgress }) {
  const [videoUrl, setVideoUrl] = useState(null)
  const [error, setError] = useState(null)
  const [showQuiz, setShowQuiz] = useState(false)
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

  // A video with quiz questions requires passing the quiz to complete —
  // reaching the end just surfaces it, exactly the "make people actually
  // watch it" mechanism this whole feature exists for. A video with no
  // quiz configured keeps the original auto-complete-on-end behavior.
  const handleEnded = () => {
    if (video.quiz_question_count > 0) {
      setShowQuiz(true)
    } else {
      markComplete()
    }
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
        onEnded={handleEnded}
      />
      {video.quiz_question_count > 0 && video.my_status !== 'completed' && !showQuiz && (
        <button onClick={() => setShowQuiz(true)} style={{ marginRight: 4 }}>Take quiz</button>
      )}
      {video.quiz_question_count === 0 && video.my_record_id && video.my_status !== 'completed' && (
        <button onClick={markComplete}>Mark as watched</button>
      )}
      {showQuiz && <VideoQuiz video={video} token={token} onDone={onProgress} />}
    </div>
  )
}

function QuizManager({ video, token }) {
  const [questions, setQuestions] = useState(null)
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ text: '', options: ['', ''], correct_index: 0 })

  const load = () => {
    apiFetch(`/quiz-questions/?video=${video.id}`, token)
      .then((data) => setQuestions(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line
  }, [])

  const addOption = () => setForm({ ...form, options: [...form.options, ''] })
  const setOption = (i, value) => {
    const options = [...form.options]
    options[i] = value
    setForm({ ...form, options })
  }

  const submit = (e) => {
    e.preventDefault()
    const options = form.options.map((o) => o.trim()).filter(Boolean)
    if (!form.text.trim() || options.length < 2) {
      setError('Add question text and at least two answer options.')
      return
    }
    apiFetch('/quiz-questions/', token, {
      method: 'POST',
      body: JSON.stringify({
        video: video.id, order: (questions || []).length, text: form.text, options,
        correct_index: Math.min(form.correct_index, options.length - 1),
      }),
    })
      .then(() => {
        setForm({ text: '', options: ['', ''], correct_index: 0 })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const remove = (q) => {
    apiFetch(`/quiz-questions/${q.id}/`, token, { method: 'DELETE' })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  return (
    <div className="workflow-card" style={{ marginTop: 8 }}>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Quiz questions (admin/auditor only) — a video with at least one question requires passing
        it ({video.pass_percent}%) to complete; failing resets the assignment back to Pending.
      </p>
      {questions === null ? (
        <p className="empty-state">Loading…</p>
      ) : questions.length === 0 ? (
        <p className="empty-state">No quiz questions yet — this video auto-completes on watch.</p>
      ) : (
        <ul style={{ paddingLeft: 20 }}>
          {questions.map((q) => (
            <li key={q.id} style={{ marginBottom: 6 }}>
              {q.text} — <em>{q.options[q.correct_index]}</em>
              <button onClick={() => remove(q)} style={{ marginLeft: 8 }}>Delete</button>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={submit} className="toolbar" style={{ flexWrap: 'wrap', marginTop: 8 }}>
        <input
          placeholder="Question text"
          value={form.text}
          onChange={(e) => setForm({ ...form, text: e.target.value })}
          style={{ width: 260 }}
        />
        {form.options.map((opt, i) => (
          <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <input
              type="radio"
              checked={form.correct_index === i}
              onChange={() => setForm({ ...form, correct_index: i })}
              title="Correct answer"
            />
            <input
              placeholder={`Option ${i + 1}`}
              value={opt}
              onChange={(e) => setOption(i, e.target.value)}
              style={{ width: 140 }}
            />
          </span>
        ))}
        <button type="button" onClick={addOption}>+ Option</button>
        <button type="submit" className="btn-primary">Add question</button>
      </form>
    </div>
  )
}

function TeamCompletion({ video, token }) {
  const [teams, setTeams] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    apiFetch(`/training-videos/${video.id}/team-completion/`, token)
      .then(setTeams)
      .catch((err) => setError(err.message))
    // eslint-disable-next-line
  }, [video.id])

  if (error) return <p className="error-text">{error}</p>
  if (teams === null) return <p className="empty-state">Loading…</p>
  if (teams.length === 0) return <p className="empty-state">No teams set up yet — see User Groups.</p>

  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'grid', gap: 8 }}>
        {teams.map((t) => (
          <div key={t.group_id} className="workflow-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <strong>{t.group_name}</strong>
              <div>
                {t.fully_trained && <span className="badge badge-success" style={{ marginRight: 6 }}>🏆 100% trained</span>}
                <span className="badge badge-neutral">{t.completed_members}/{t.total_members} ({t.percent}%)</span>
              </div>
            </div>
            {t.members.length > 0 && (
              <table style={{ marginTop: 8 }}>
                <thead>
                  <tr>
                    <th>Member</th>
                    <th>Status</th>
                    <th>Streak</th>
                  </tr>
                </thead>
                <tbody>
                  {t.members.map((m) => (
                    <tr key={m.username}>
                      <td>{m.username}</td>
                      <td>{m.status ? <StatusBadge value={m.status} /> : '—'}</td>
                      <td>{m.streak > 0 ? `🔥 ${m.streak}` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ))}
      </div>
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
  const [quizManagerId, setQuizManagerId] = useState(null)
  const [teamCompletionId, setTeamCompletionId] = useState(null)

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
        Completed tracked per person below. Add quiz questions ("Manage quiz") to require actually
        passing a quick check before a video counts as watched — failing resets it back to
        Pending. "Team completion" shows each User Group's progress, a 🏆 100% trained badge once
        everyone's done, and each person's current streak of completed videos.
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
                  <button onClick={() => setQuizManagerId(quizManagerId === v.id ? null : v.id)}>
                    {quizManagerId === v.id ? 'Hide quiz' : `Manage quiz (${v.quiz_question_count})`}
                  </button>
                  <button onClick={() => setTeamCompletionId(teamCompletionId === v.id ? null : v.id)}>
                    {teamCompletionId === v.id ? 'Hide teams' : 'Team completion'}
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

              {quizManagerId === v.id && <QuizManager video={v} token={token} />}
              {teamCompletionId === v.id && <TeamCompletion video={v} token={token} />}
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
