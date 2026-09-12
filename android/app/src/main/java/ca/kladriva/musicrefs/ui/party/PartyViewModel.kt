package ca.kladriva.musicrefs.ui.party

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import ca.kladriva.musicrefs.data.api.ApiResult
import ca.kladriva.musicrefs.data.model.CategoryDto
import ca.kladriva.musicrefs.data.model.GameMode
import ca.kladriva.musicrefs.data.model.PartyPlayerDto
import ca.kladriva.musicrefs.data.model.PartySnapshotDto
import ca.kladriva.musicrefs.data.prefs.UserPreferences
import ca.kladriva.musicrefs.data.repository.MusicRefsRepository
import ca.kladriva.musicrefs.domain.game.GameEngine
import ca.kladriva.musicrefs.domain.game.QuizChoices
import ca.kladriva.musicrefs.domain.game.Quote
import ca.kladriva.musicrefs.domain.game.buildQuizChoices
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PartyHubState(
    val categories: List<CategoryDto> = emptyList(),
    val selectedCategoryId: Int? = null,
    val hostName: String = "",
    val joinName: String = "",
    val joinCode: String = "",
    val roundLimit: Int = 8,
    val mode: GameMode = GameMode.CLASSIC,
    val deepLinkCode: String? = null,
    val loading: Boolean = false,
)

data class PartySessionState(
    val snapshot: PartySnapshotDto? = null,
    val playerToken: String? = null,
    val hostToken: String? = null,
    val myName: String? = null,
    val quote: Quote? = null,
    val score: Int = 0,
    val streak: Int = 0,
    val highScore: Int = 0,
    val artistInput: String = "",
    val titleInput: String = "",
    val artistGuessed: Boolean = false,
    val titleGuessed: Boolean = false,
    val revealedHints: Map<String, String> = emptyMap(),
    val feedback: String? = null,
    val mode: GameMode = GameMode.CLASSIC,
    val quiz: QuizChoices? = null,
    val selectedArtist: String? = null,
    val selectedTitle: String? = null,
    val progressLabel: String = "0 / 0",
    val locallyFinished: Boolean = false,
    val waitingOthers: Boolean = false,
)

@HiltViewModel
class PartyViewModel @Inject constructor(
    private val repository: MusicRefsRepository,
    private val prefs: UserPreferences,
    @ApplicationContext private val appContext: Context,
) : ViewModel() {

    private val _hub = MutableStateFlow(PartyHubState())
    val hub: StateFlow<PartyHubState> = _hub.asStateFlow()

    private val _session = MutableStateFlow(PartySessionState())
    val session: StateFlow<PartySessionState> = _session.asStateFlow()

    private val _messages = MutableSharedFlow<String>()
    val messages: SharedFlow<String> = _messages.asSharedFlow()

    private val _navEvents = MutableSharedFlow<PartyNav>()
    val navEvents: SharedFlow<PartyNav> = _navEvents.asSharedFlow()

    private var engine: GameEngine? = null
    private var pool: List<Quote> = emptyList()
    private var pollJob: Job? = null

    init {
        viewModelScope.launch {
            val name = prefs.getPlayerName()
            _hub.update { it.copy(hostName = name, joinName = name) }
            loadCategories()
        }
    }

    fun loadCategories() {
        viewModelScope.launch {
            when (val res = repository.categories()) {
                is ApiResult.Ok -> {
                    val first = res.value.firstOrNull()?.id
                    _hub.update {
                        it.copy(
                            categories = res.value,
                            selectedCategoryId = it.selectedCategoryId ?: first,
                        )
                    }
                }
                is ApiResult.Err -> _messages.emit(res.message)
            }
        }
    }

    fun setDeepLinkCode(code: String?) {
        if (code.isNullOrBlank()) return
        _hub.update {
            it.copy(deepLinkCode = code.uppercase(), joinCode = code.uppercase())
        }
    }

    fun updateHub(
        hostName: String? = null,
        joinName: String? = null,
        joinCode: String? = null,
        categoryId: Int? = null,
        rounds: Int? = null,
        mode: GameMode? = null,
    ) {
        _hub.update {
            it.copy(
                hostName = hostName ?: it.hostName,
                joinName = joinName ?: it.joinName,
                joinCode = joinCode ?: it.joinCode,
                selectedCategoryId = categoryId ?: it.selectedCategoryId,
                roundLimit = rounds ?: it.roundLimit,
                mode = mode ?: it.mode,
            )
        }
    }

    fun createParty() {
        viewModelScope.launch {
            val h = _hub.value
            val cat = h.selectedCategoryId ?: run {
                _messages.emit("Choisis une catégorie")
                return@launch
            }
            if (h.hostName.isBlank()) {
                _messages.emit("Entre ton prénom")
                return@launch
            }
            _hub.update { it.copy(loading = true) }
            prefs.savePlayerName(h.hostName)
            when (
                val res = repository.createParty(
                    categoryId = cat,
                    hostName = h.hostName.trim(),
                    roundLimit = h.roundLimit.coerceIn(3, 30),
                    mode = h.mode,
                )
            ) {
                is ApiResult.Ok -> {
                    applySnapshot(res.value, keepTokens = true)
                    _hub.update { it.copy(loading = false) }
                    startPolling()
                    _navEvents.emit(PartyNav.Lobby)
                }
                is ApiResult.Err -> {
                    _hub.update { it.copy(loading = false) }
                    _messages.emit(res.message)
                }
            }
        }
    }

    fun joinParty() {
        viewModelScope.launch {
            val h = _hub.value
            if (h.joinName.isBlank() || h.joinCode.isBlank()) {
                _messages.emit("Prénom et code requis")
                return@launch
            }
            _hub.update { it.copy(loading = true) }
            prefs.savePlayerName(h.joinName)
            when (val res = repository.joinParty(h.joinCode, h.joinName.trim())) {
                is ApiResult.Ok -> {
                    applySnapshot(res.value, keepTokens = true)
                    _hub.update { it.copy(loading = false, deepLinkCode = null) }
                    startPolling()
                    _navEvents.emit(PartyNav.Lobby)
                }
                is ApiResult.Err -> {
                    _hub.update { it.copy(loading = false) }
                    _messages.emit(res.message)
                }
            }
        }
    }

    fun startParty() {
        viewModelScope.launch {
            val s = _session.value
            val code = s.snapshot?.code ?: return@launch
            val token = s.hostToken ?: run {
                _messages.emit("Seul l'hôte peut lancer")
                return@launch
            }
            when (val res = repository.startParty(code, token)) {
                is ApiResult.Ok -> {
                    applySnapshot(res.value, keepTokens = true)
                    beginPlaying()
                }
                is ApiResult.Err -> _messages.emit(res.message)
            }
        }
    }

    private suspend fun beginPlaying() {
        val code = _session.value.snapshot?.code ?: return
        when (val res = repository.partyQuotes(code)) {
            is ApiResult.Ok -> {
                pool = res.value
                val high = prefs.getHighScore()
                engine = GameEngine(
                    quotesList = pool,
                    highScoreProvider = { high },
                    highScoreSaver = { score -> viewModelScope.launch { prefs.saveHighScore(score) } },
                ).also { it.setQuotes(pool, ordered = true) }
                syncPlay(clearInputs = true)
                syncScore(finished = false)
                _navEvents.emit(PartyNav.Play)
            }
            is ApiResult.Err -> _messages.emit(res.message)
        }
    }

    fun onArtistChange(v: String) = _session.update { it.copy(artistInput = v) }
    fun onTitleChange(v: String) = _session.update { it.copy(titleInput = v) }

    fun selectQuizArtist(v: String) {
        _session.update { it.copy(selectedArtist = v) }
        maybeAutoSubmit()
    }

    fun selectQuizTitle(v: String) {
        _session.update { it.copy(selectedTitle = v) }
        maybeAutoSubmit()
    }

    private fun maybeAutoSubmit() {
        val s = _session.value
        if (s.mode != GameMode.EASY) return
        val a = s.selectedArtist ?: return
        val t = s.selectedTitle ?: return
        validate(a, t)
    }

    fun validate(artist: String? = null, title: String? = null) {
        val e = engine ?: return
        if (_session.value.locallyFinished) return
        val s = _session.value
        val result = e.validateAnswer(artist ?: s.artistInput, title ?: s.titleInput)
        syncPlay(feedback = result.message)
        viewModelScope.launch { syncScore(finished = false) }
        if (result.isFullyGuessed) {
            // wait for next press
        }
    }

    fun revealHint(type: String) {
        val e = engine ?: return
        val res = e.revealHint(type)
        if (res.success) {
            syncPlay(feedback = "Indice (−20 pts) : ${res.value}")
        } else {
            viewModelScope.launch { _messages.emit(res.reason ?: "Indice indisponible") }
        }
    }

    fun nextRound() {
        val e = engine ?: return
        if (_session.value.locallyFinished) return
        val fully = _session.value.artistGuessed && _session.value.titleGuessed
        if (!fully) {
            e.resetStreak()
        }
        val next = e.advanceOrdered()
        if (next == null) {
            finishLocal()
        } else {
            syncPlay(
                clearInputs = true,
                feedback = if (fully) null else "Punchline passée",
            )
            viewModelScope.launch { syncScore(finished = false) }
        }
    }

    private fun finishLocal() {
        viewModelScope.launch {
            syncScore(finished = true)
            _session.update { it.copy(locallyFinished = true, waitingOthers = true) }
            // keep polling until party finished
        }
    }

    private suspend fun syncScore(finished: Boolean) {
        val s = _session.value
        val code = s.snapshot?.code ?: return
        val token = s.playerToken ?: return
        val e = engine
        val progress = e?.progressOneBased() ?: s.snapshot?.me?.progress
        when (
            val res = repository.updateScore(
                code = code,
                playerToken = token,
                score = e?.score ?: s.score,
                finished = finished,
                progress = progress,
            )
        ) {
            is ApiResult.Ok -> applySnapshot(res.value, keepTokens = true)
            is ApiResult.Err -> _messages.emit(res.message)
        }
    }

    fun shareInvite() {
        val code = _session.value.snapshot?.code ?: return
        val link = "https://music-refs-dev.kladriva.ca/party.html?code=$code"
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, "Rejoins ma partie Music Refs ! Code $code\n$link")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        appContext.startActivity(Intent.createChooser(intent, "Partager").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    fun leave() {
        stopPolling()
        engine = null
        pool = emptyList()
        _session.value = PartySessionState()
    }

    private fun applySnapshot(snap: PartySnapshotDto, keepTokens: Boolean) {
        val prev = _session.value
        val me = snap.me
        _session.update {
            it.copy(
                snapshot = snap,
                playerToken = if (keepTokens) (me?.playerToken ?: it.playerToken) else it.playerToken,
                hostToken = if (keepTokens) (me?.hostToken ?: it.hostToken) else it.hostToken,
                myName = me?.name ?: it.myName,
                mode = GameMode.fromApi(snap.mode),
            )
        }
        when (snap.status) {
            "playing" -> {
                if (engine == null && prev.snapshot?.status != "playing") {
                    viewModelScope.launch { beginPlaying() }
                }
            }
            "finished" -> {
                stopPolling()
                viewModelScope.launch { _navEvents.emit(PartyNav.Results) }
            }
        }
    }

    private fun syncPlay(feedback: String? = null, clearInputs: Boolean = false) {
        val e = engine ?: return
        val mode = _session.value.mode
        val quiz = if (mode == GameMode.EASY) buildQuizChoices(e.currentQuote, pool) else null
        _session.update {
            it.copy(
                quote = e.currentQuote,
                score = e.score,
                streak = e.streak,
                highScore = e.highScore,
                artistGuessed = e.artistGuessed,
                titleGuessed = e.titleGuessed,
                revealedHints = e.revealedHints.associateWith { type ->
                    e.currentQuote?.hints?.get(type).orEmpty()
                }.filterValues { v -> v.isNotBlank() },
                feedback = feedback,
                quiz = quiz,
                progressLabel = "${e.orderIndex + 1} / ${e.quotes.size}",
                artistInput = if (clearInputs) "" else it.artistInput,
                titleInput = if (clearInputs) "" else it.titleInput,
                selectedArtist = if (clearInputs) null else it.selectedArtist,
                selectedTitle = if (clearInputs) null else it.selectedTitle,
            )
        }
    }

    fun startPolling() {
        pollJob?.cancel()
        pollJob = viewModelScope.launch {
            while (isActive) {
                val code = _session.value.snapshot?.code
                if (code == null) break
                val status = _session.value.snapshot?.status
                if (status == "finished") break
                when (val res = repository.party(code)) {
                    is ApiResult.Ok -> applySnapshot(res.value, keepTokens = true)
                    is ApiResult.Err -> { /* soft fail */ }
                }
                delay(1500)
            }
        }
    }

    fun stopPolling() {
        pollJob?.cancel()
        pollJob = null
    }

    override fun onCleared() {
        stopPolling()
        super.onCleared()
    }

    fun rankedPlayers(): List<PartyPlayerDto> {
        val players = _session.value.snapshot?.players.orEmpty()
        return players.sortedWith(
            compareByDescending<PartyPlayerDto> { it.score }
                .thenByDescending { it.progress },
        )
    }
}

sealed class PartyNav {
    data object Lobby : PartyNav()
    data object Play : PartyNav()
    data object Results : PartyNav()
}
