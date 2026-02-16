/**
 * useVillageTasking — Task Execution Bridge for Village Interface
 *
 * Connects VillageTaskDialog output to existing backend APIs.
 * Handles single-agent chat, multi-agent council, file uploads,
 * and streams results back to the Village scene.
 *
 * "The bridge between clicking a building and watching magic happen"
 */

import { ref, shallowRef } from 'vue'
import api from '@/services/api'

// Tool categories mapped to zones (matches PHASE-E-PLAN.md)
const ZONE_TOOL_CATEGORIES = {
  workshop: ['utility', 'files'],
  library: ['web', 'browser'],
  dj_booth: ['music', 'creative'],
  memory_garden: ['memory'],
  file_shed: ['files', 'utility'],
  bridge_portal: ['web', 'agent'],
  watchtower: ['utility', 'web'],
  village_square: null, // All tools
}

export function useVillageTasking() {
  // --- Reactive state ---
  const isExecuting = ref(false)
  const currentTask = shallowRef(null) // { zone, prompt, agents, mode, status }
  const taskResult = ref(null) // { content, conversationId, success, duration }
  const taskError = ref(null)
  const streamingContent = ref('')
  const streamingAgent = ref(null)

  // Task history (persisted in memory for session)
  const taskHistory = ref([])

  // Abort controller for cancelling in-flight requests
  let abortController = null

  // =========================================================================
  // EXECUTE TASK
  // =========================================================================

  /**
   * Main entry point — dispatches to single-agent or council flow.
   * @param {Object} task - { prompt, agents[], mode, zone, files[], useTools, conversationId? }
   * @returns {Promise<Object>} result or null on error
   */
  async function executeTask(task) {
    if (isExecuting.value) return null

    isExecuting.value = true
    taskError.value = null
    taskResult.value = null
    streamingContent.value = ''
    streamingAgent.value = task.agents[0] || null

    currentTask.value = {
      ...task,
      status: 'running',
      startTime: Date.now(),
    }

    abortController = new AbortController()

    try {
      // Upload files first if any
      let fileIds = []
      if (task.files?.length > 0) {
        fileIds = await _uploadFiles(task.files)
      }

      let result
      if (task.mode === 'council' && task.agents.length > 1) {
        result = await _executeCouncil(task, fileIds)
      } else {
        result = await _executeSingleAgent(task, fileIds)
      }

      // Record in history
      const historyEntry = {
        id: Date.now().toString(),
        zone: task.zone,
        prompt: task.prompt,
        agents: task.agents,
        mode: task.mode,
        result: result?.content?.slice(0, 500),
        conversationId: result?.conversationId,
        success: true,
        duration: Date.now() - currentTask.value.startTime,
        timestamp: new Date().toISOString(),
      }
      taskHistory.value.unshift(historyEntry)
      if (taskHistory.value.length > 50) taskHistory.value.pop()

      taskResult.value = result
      currentTask.value = { ...currentTask.value, status: 'complete' }

      return result
    } catch (error) {
      if (error.name === 'AbortError') {
        taskError.value = 'Task cancelled'
      } else {
        taskError.value = error.message || 'Task failed'
        console.error('[VillageTasking] Error:', error)
      }

      currentTask.value = { ...currentTask.value, status: 'error' }

      // Record failed task in history
      taskHistory.value.unshift({
        id: Date.now().toString(),
        zone: task.zone,
        prompt: task.prompt,
        agents: task.agents,
        mode: task.mode,
        result: taskError.value,
        success: false,
        duration: Date.now() - (currentTask.value?.startTime || Date.now()),
        timestamp: new Date().toISOString(),
      })

      return null
    } finally {
      isExecuting.value = false
      abortController = null
    }
  }

  // =========================================================================
  // SINGLE AGENT — SSE Streaming via POST /api/v1/chat/message
  // =========================================================================

  async function _executeSingleAgent(task, fileIds) {
    let apiUrl = import.meta.env.VITE_API_URL || ''
    if (apiUrl && !apiUrl.startsWith('http://') && !apiUrl.startsWith('https://')) {
      apiUrl = 'https://' + apiUrl
    }

    const token = localStorage.getItem('accessToken')
    if (!token) throw new Error('Not authenticated')

    const toolCategories = task.useTools
      ? (ZONE_TOOL_CATEGORIES[task.zone] || null)
      : undefined

    const response = await fetch(`${apiUrl}/api/v1/chat/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        message: task.prompt,
        agent: task.agents[0] || 'AZOTH',
        stream: true,
        use_tools: task.useTools !== false,
        max_tokens: 4096,
        ...(toolCategories && { tool_categories: toolCategories }),
        ...(fileIds.length > 0 && { file_ids: fileIds }),
        ...(task.conversationId && { conversation_id: task.conversationId }),
      }),
      signal: abortController.signal,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const detail = errorData.detail
      if (typeof detail === 'object') {
        throw new Error(detail.message || detail.error || `HTTP ${response.status}`)
      }
      throw new Error(detail || `HTTP ${response.status}`)
    }

    // Read SSE stream
    let conversationId = null
    let content = ''
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))

          if (data.type === 'token' && data.content) {
            content += data.content
            streamingContent.value = content
          } else if (data.type === 'start' && data.conversation_id) {
            conversationId = data.conversation_id
          } else if (data.type === 'tool_start') {
            streamingContent.value = content + `\n\n**Using: ${data.tool_name}...**\n`
          } else if (data.type === 'tool_result') {
            const status = data.is_error ? 'Error' : 'Done'
            const preview = typeof data.result === 'string'
              ? data.result.slice(0, 300)
              : JSON.stringify(data.result, null, 2).slice(0, 300)
            content += `\n\n**${data.name}** (${status}):\n\`\`\`\n${preview}\n\`\`\`\n\n`
            streamingContent.value = content
          } else if (data.type === 'error') {
            throw new Error(data.message || 'Stream error')
          }
        } catch (parseError) {
          if (parseError.message?.includes('Stream error') || parseError.message?.includes('HTTP')) {
            throw parseError
          }
        }
      }
    }

    return {
      content,
      conversationId,
      success: true,
      agent: task.agents[0],
    }
  }

  // =========================================================================
  // COUNCIL — Multi-agent deliberation
  // =========================================================================

  async function _executeCouncil(task, fileIds) {
    let apiUrl = import.meta.env.VITE_API_URL || ''
    if (apiUrl && !apiUrl.startsWith('http://') && !apiUrl.startsWith('https://')) {
      apiUrl = 'https://' + apiUrl
    }

    const token = localStorage.getItem('accessToken')
    if (!token) throw new Error('Not authenticated')

    const toolCategories = task.useTools
      ? (ZONE_TOOL_CATEGORIES[task.zone] || ['utility', 'web', 'files'])
      : []

    // 1. Create council session
    const sessionRes = await api.post('/api/v1/council/sessions', {
      topic: task.prompt,
      agents: task.agents,
      max_rounds: 5,
      use_tools: task.useTools !== false,
      tool_categories: toolCategories,
    })

    const sessionId = sessionRes.data.id
    if (!sessionId) throw new Error('Failed to create council session')

    // 2. Auto-deliberate with SSE streaming
    const response = await fetch(
      `${apiUrl}/api/v1/council/sessions/${sessionId}/auto-deliberate?num_rounds=5`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        signal: abortController.signal,
      }
    )

    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || `Council HTTP ${response.status}`)
    }

    // Read SSE stream
    let content = ''
    let currentRound = 0
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))

          if (data.type === 'round_start') {
            currentRound = data.round
            content += `\n---\n**Round ${currentRound}**\n\n`
            streamingContent.value = content
          } else if (data.type === 'agent_complete') {
            streamingAgent.value = data.agent_id
            const agentContent = data.content || data.text || ''
            content += `**${data.agent_id}:** ${agentContent}\n\n`
            streamingContent.value = content
          } else if (data.type === 'consensus') {
            content += `\n---\n**Consensus:**\n${data.summary || data.content || ''}\n`
            streamingContent.value = content
          } else if (data.type === 'end') {
            // Done
          } else if (data.type === 'error') {
            throw new Error(data.message || 'Council stream error')
          }
        } catch (parseError) {
          if (parseError.message?.includes('error') || parseError.message?.includes('HTTP')) {
            throw parseError
          }
        }
      }
    }

    return {
      content,
      conversationId: sessionId,
      success: true,
      agents: task.agents,
      isCouncil: true,
    }
  }

  // =========================================================================
  // FILE UPLOAD
  // =========================================================================

  async function _uploadFiles(fileList) {
    const ids = []

    for (const file of fileList) {
      try {
        const formData = new FormData()
        formData.append('file', file)

        const response = await api.post('/api/v1/files/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })

        if (response.data?.id) {
          ids.push(response.data.id)
        }
      } catch (error) {
        console.warn('[VillageTasking] File upload failed:', file.name, error.message)
        // Continue with other files — don't fail the whole task
      }
    }

    return ids
  }

  // =========================================================================
  // CANCEL
  // =========================================================================

  function cancelTask() {
    if (abortController) {
      abortController.abort()
    }
    isExecuting.value = false
    currentTask.value = null
  }

  // =========================================================================
  // CLEANUP
  // =========================================================================

  function clearResult() {
    taskResult.value = null
    taskError.value = null
    streamingContent.value = ''
    streamingAgent.value = null
    currentTask.value = null
  }

  return {
    // State
    isExecuting,
    currentTask,
    taskResult,
    taskError,
    streamingContent,
    streamingAgent,
    taskHistory,

    // Actions
    executeTask,
    cancelTask,
    clearResult,
  }
}
