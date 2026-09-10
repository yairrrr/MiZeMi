export const GAME_STATES = [
  'LOBBY',
  'PROFILE_COLLECTION',
  'READY',
  'QUESTION_ACTIVE',
  'QUESTION_RESULTS',
  'LEADERBOARD',
  'FINISHED',
] as const

export type GameState = (typeof GAME_STATES)[number]

export type Player = {
  player_id: string
  display_name: string
  is_host: boolean
  connected: boolean
  has_profile: boolean
  is_ready: boolean
  score: number
}

export type ProfileField = {
  field_key: string
  value: string | number
  allow_question_usage: boolean
}

export type PlayerProfile = {
  player_id: string
  fields: ProfileField[]
}

export type QuestionOption = {
  option_id: string
  text: string
}

export type Question = {
  question_id: string
  index: number
  total_questions: number
  question_type: 'multiple_choice'
  text: string
  options: QuestionOption[]
  time_limit_seconds: number
  started_at: string
}

export type AnswerSubmission = {
  question_id: string
  option_id: string
}

export type Score = {
  player_id: string
  total_score: number
}

export type AnswerDistributionEntry = {
  option_id: string
  count: number
}

export type Statistics = {
  question_id: string
  correct_option_id: string
  answer_distribution: AnswerDistributionEntry[]
  answered_count: number
  player_count: number
}

export type LeaderboardEntry = {
  rank: number
  player_id: string
  display_name: string
  total_score: number
}

export type Leaderboard = {
  entries: LeaderboardEntry[]
}

export type CreateRoomResponse = {
  room_code: string
  game_id: string
}

export type JoinRoomRequest = {
  display_name: string
}

export type JoinRoomResponse = {
  game_id: string
  player: Player
}

export const ERROR_CODES = [
  'ROOM_NOT_FOUND',
  'ROOM_FULL',
  'NAME_TAKEN',
  'INVALID_STATE_TRANSITION',
  'QUESTION_CLOSED',
  'ALREADY_ANSWERED',
  'NOT_HOST',
  'VALIDATION_ERROR',
  'UNKNOWN_EVENT',
  'INTERNAL_ERROR',
  'ROOM_NOT_JOINABLE',
] as const

export type ErrorCode = (typeof ERROR_CODES)[number]

export type ErrorResponse = {
  error: {
    code: ErrorCode
    message: string
    details?: Record<string, unknown>
  }
}
