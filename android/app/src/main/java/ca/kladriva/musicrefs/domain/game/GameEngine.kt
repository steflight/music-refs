package ca.kladriva.musicrefs.domain.game

import java.text.Normalizer
import kotlin.math.min
import kotlin.random.Random

fun normalizeString(str: String?): String {
    if (str.isNullOrBlank()) return ""
    val nfd = Normalizer.normalize(str.lowercase(), Normalizer.Form.NFD)
    val noAccents = nfd.replace(Regex("\\p{Mn}+"), "")
    return noAccents.replace(Regex("[^a-z0-9]"), "")
}

fun levenshteinDistance(a: String, b: String): Int {
    val matrix = Array(a.length + 1) { IntArray(b.length + 1) }
    for (i in 0..a.length) matrix[i][0] = i
    for (j in 0..b.length) matrix[0][j] = j
    for (i in 1..a.length) {
        for (j in 1..b.length) {
            val cost = if (a[i - 1] == b[j - 1]) 0 else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                min(matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + cost),
            )
        }
    }
    return matrix[a.length][b.length]
}

fun isMatch(input: String?, target: String?): Boolean {
    val normInput = normalizeString(input)
    val normTarget = normalizeString(target)
    if (normInput.isEmpty() || normTarget.isEmpty()) return false
    if (normInput == normTarget) return true
    if (normInput.length >= 3) {
        if (normTarget.contains(normInput) || normInput.contains(normTarget)) return true
    }
    val dist = levenshteinDistance(normInput, normTarget)
    val maxAllowed = if (normTarget.length > 6) 2 else 1
    return dist <= maxAllowed
}

data class QuizChoices(
    val artists: List<String>,
    val titles: List<String>,
)

fun buildQuizChoices(
    currentQuote: Quote?,
    pool: List<Quote>,
    count: Int = 4,
    random: Random = Random.Default,
): QuizChoices {
    if (currentQuote == null) return QuizChoices(emptyList(), emptyList())
    val others = pool.filter { it.id != currentQuote.id }

    fun pickField(field: (Quote) -> String, correct: String, isArtist: Boolean): List<String> {
        val uniq = mutableSetOf<String>()
        val options = mutableListOf(correct)
        uniq.add(normalizeString(correct))
        val shuffled = others.shuffled(random)
        for (q in shuffled) {
            val value = field(q).trim()
            if (value.isEmpty()) continue
            val n = normalizeString(value)
            if (n in uniq) continue
            uniq.add(n)
            options.add(value)
            if (options.size >= count) break
        }
        val fillers = if (isArtist) {
            listOf("Artiste Mystère", "Inconnu·e", "Anonymous", "DJ X")
        } else {
            listOf("Sans titre", "Track #1", "Bonus", "Interlude")
        }
        for (f in fillers) {
            if (options.size >= count) break
            val n = normalizeString(f)
            if (n in uniq) continue
            uniq.add(n)
            options.add(f)
        }
        return options.shuffled(random)
    }

    return QuizChoices(
        artists = pickField(Quote::artist, currentQuote.artist, isArtist = true),
        titles = pickField(Quote::title, currentQuote.title, isArtist = false),
    )
}

data class Hints(
    val year: String = "",
    val genre: String = "",
    val album: String = "",
    val initials: String = "",
) {
    fun get(type: String): String? = when (type) {
        "year" -> year.takeIf { it.isNotBlank() }
        "genre" -> genre.takeIf { it.isNotBlank() }
        "album" -> album.takeIf { it.isNotBlank() }
        "initials" -> initials.takeIf { it.isNotBlank() }
        else -> null
    }
}

data class Quote(
    val id: Int,
    val quote: String,
    val artist: String,
    val title: String,
    val hints: Hints = Hints(),
    val categoryIds: List<Int> = emptyList(),
)

data class HintRevealResult(
    val success: Boolean,
    val reason: String? = null,
    val hintType: String? = null,
    val value: String? = null,
    val revealedCount: Int = 0,
)

data class ValidationResult(
    val success: Boolean,
    val message: String,
    val artistMatched: Boolean = false,
    val titleMatched: Boolean = false,
    val isFullyGuessed: Boolean = false,
    val pointsGained: Int = 0,
    val streak: Int = 0,
    val score: Int = 0,
    val highScore: Int = 0,
)

data class SkipResult(
    val previousQuote: Quote?,
    val nextQuote: Quote?,
    val score: Int,
    val streak: Int,
)

data class ResetResult(
    val score: Int,
    val streak: Int,
    val highScore: Int,
    val quote: Quote?,
)

class GameEngine(
    quotesList: List<Quote> = emptyList(),
    private var highScoreProvider: () -> Int = { 0 },
    private var highScoreSaver: (Int) -> Unit = {},
) {
    var quotes: MutableList<Quote> = quotesList.toMutableList()
        private set
    private val playedIds = mutableSetOf<Int>()
    var currentQuote: Quote? = null
        private set
    var score: Int = 0
        private set
    var streak: Int = 0
        private set
    var highScore: Int = highScoreProvider()
        private set
    val revealedHints = mutableSetOf<String>()
    var artistGuessed: Boolean = false
        private set
    var titleGuessed: Boolean = false
        private set
    var totalAttempts: Int = 0
        private set
    var successfulQuotes: Int = 0
        private set
    var orderedMode: Boolean = false
        private set
    var orderIndex: Int = 0
        private set

    init {
        if (quotes.isNotEmpty()) selectRandomQuote()
    }

    fun setQuotes(quotesList: List<Quote>, ordered: Boolean = false): Quote? {
        quotes = if (quotesList.isNotEmpty()) quotesList.toMutableList() else mutableListOf()
        playedIds.clear()
        orderedMode = ordered
        orderIndex = 0
        return if (orderedMode) {
            selectOrderedQuote(0)
        } else {
            selectRandomQuote()
            currentQuote
        }
    }

    fun selectOrderedQuote(index: Int = 0): Quote? {
        revealedHints.clear()
        artistGuessed = false
        titleGuessed = false
        if (quotes.isEmpty()) {
            currentQuote = null
            return null
        }
        orderIndex = index.coerceIn(0, quotes.lastIndex)
        currentQuote = quotes[orderIndex]
        playedIds.add(currentQuote!!.id)
        return currentQuote
    }

    fun advanceOrdered(): Quote? {
        if (!orderedMode) return selectRandomQuote()
        if (orderIndex >= quotes.lastIndex) return null
        return selectOrderedQuote(orderIndex + 1)
    }

    fun isPartyComplete(): Boolean =
        orderedMode && orderIndex >= quotes.lastIndex && artistGuessed && titleGuessed

    fun selectRandomQuote(): Quote? {
        revealedHints.clear()
        artistGuessed = false
        titleGuessed = false
        if (quotes.isEmpty()) {
            currentQuote = null
            return null
        }
        if (playedIds.size >= quotes.size) playedIds.clear()
        val available = quotes.filter { it.id !in playedIds }
        currentQuote = if (available.isEmpty()) {
            quotes.first()
        } else {
            available.random()
        }
        playedIds.add(currentQuote!!.id)
        return currentQuote
    }

    fun revealHint(hintType: String): HintRevealResult {
        val quote = currentQuote
        val value = quote?.hints?.get(hintType)
        if (quote == null || value == null) {
            return HintRevealResult(success = false, reason = "Hint not available")
        }
        if (hintType in revealedHints) {
            return HintRevealResult(success = false, reason = "Hint already revealed")
        }
        revealedHints.add(hintType)
        return HintRevealResult(
            success = true,
            hintType = hintType,
            value = value,
            revealedCount = revealedHints.size,
        )
    }

    fun validateAnswer(inputArtist: String?, inputTitle: String?): ValidationResult {
        val quote = currentQuote
            ?: return ValidationResult(success = false, message = "No active quote")

        var artistMatch = false
        var titleMatch = false

        if (!inputArtist.isNullOrBlank() && !artistGuessed) {
            artistMatch = isMatch(inputArtist, quote.artist)
        }
        if (!inputTitle.isNullOrBlank() && !titleGuessed) {
            titleMatch = isMatch(inputTitle, quote.title)
        }

        if (inputTitle.isNullOrBlank() && !inputArtist.isNullOrBlank()) {
            if (!artistGuessed && isMatch(inputArtist, quote.artist)) artistMatch = true
            if (!titleGuessed && isMatch(inputArtist, quote.title)) titleMatch = true
        }

        totalAttempts++
        var pointsGained = 0
        val feedback = mutableListOf<String>()

        if (artistMatch && !artistGuessed) {
            artistGuessed = true
            pointsGained += 100
            feedback.add("Artiste trouvé: ${quote.artist}")
        }
        if (titleMatch && !titleGuessed) {
            titleGuessed = true
            pointsGained += 100
            feedback.add("Titre trouvé: ${quote.title}")
        }

        val isFullyGuessed = artistGuessed && titleGuessed

        if (pointsGained > 0) {
            val hintPenalty = revealedHints.size * 20
            pointsGained = maxOf(20, pointsGained - hintPenalty)
            if (isFullyGuessed) {
                streak++
                successfulQuotes++
                val streakBonus = (streak - 1) * 50
                pointsGained += 50 + streakBonus
            }
            score += pointsGained
            saveHighScore(score)
            return ValidationResult(
                success = true,
                artistMatched = artistMatch,
                titleMatched = titleMatch,
                isFullyGuessed = isFullyGuessed,
                pointsGained = pointsGained,
                streak = streak,
                score = score,
                highScore = highScore,
                message = feedback.joinToString(" | ").ifBlank { "Bonne réponse !" },
            )
        }

        if (!artistGuessed && !titleGuessed) {
            streak = 0
        }
        return ValidationResult(
            success = false,
            pointsGained = 0,
            streak = streak,
            score = score,
            highScore = highScore,
            message = "Mauvaise réponse. Réessayez ou demandez un indice !",
        )
    }

    fun resetStreak() {
        streak = 0
    }

    fun skipQuote(): SkipResult {
        streak = 0
        val previous = currentQuote
        val next = selectRandomQuote()
        return SkipResult(previous, next, score, streak)
    }

    fun resetGame(): ResetResult {
        score = 0
        streak = 0
        playedIds.clear()
        totalAttempts = 0
        successfulQuotes = 0
        selectRandomQuote()
        return ResetResult(score, streak, highScore, currentQuote)
    }

    private fun saveHighScore(newScore: Int) {
        if (newScore > highScore) {
            highScore = newScore
            highScoreSaver(newScore)
        }
    }

    /** Progress 1-based for party sync. */
    fun progressOneBased(): Int = if (quotes.isEmpty()) 0 else orderIndex + 1
}
