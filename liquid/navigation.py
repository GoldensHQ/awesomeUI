import time

from PySide6.QtCore import (
    QCoreApplication,
    QEasingCurve,
    QEvent,
    QSize,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme import ColorThemeManager, theme_pixmap
from src.gui.window_chrome import (
    CONTROLS_RIGHT,
    CONTROLS_TRAILING_INSET,
    FLAT_BUTTON_H,
)

from .controls import GlassPanel, LiquidButton

#: Top margin of the header content. macOS keeps the band its traffic lights
#: float over; the flat chrome (Windows/Linux) puts the caption buttons in the
#: top-right corner, so there the header moves up into that band instead.
TOP_MARGIN = 8 if CONTROLS_RIGHT else 44

#: Header height (category pills hidden / shown). The flat header starts higher,
#: so it is that much shorter — the content box stays exactly the same.
_HEIGHT = 94 - (44 - TOP_MARGIN)
_HEIGHT_PILLS = 128 - (44 - TOP_MARGIN)

# Ensure resources are registered (icons used below)
try:
    from src.qt import resources_rc  # noqa: F401  (side-effect: registers :/icon Qt resources)
except Exception:
    resources_rc = None


class BackCapsule(LiquidButton):
    """Header's back button: a pill with a chevron icon and the word "Back".

    It floats over the header's left edge, right below the app-drawn window
    buttons (close / minimize / zoom), and refits its width to the label on
    every change so live translation cannot clip the word.
    """

    labelFitted=Signal(int)

    def __init__(self,parent=None):
        super().__init__('',parent)
        self.setIconSize(QSize(16,16))
        if CONTROLS_RIGHT:
            # The back zone mirrors the caption-button band on the right:
            # its height, and its full width, so the glass fills the flank.
            self.setFixedHeight(FLAT_BUTTON_H)
            self.setMinimumWidth(CONTROLS_TRAILING_INSET)
        else:
            self.setFixedHeight(36)
        self.setStyleSheet('QPushButton#liquidButton { background:transparent; border:none; padding:4px 16px; font-size:15px; font-weight:600; text-align:center; }')

    def fit_to_label(self):
        width=max(96,self.sizeHint().width())
        if CONTROLS_RIGHT:
            # The layout parks the pill on the flank: never wider than the
            # zone a translation hint can ougrow to nothing but minimum.
            self.setMinimumWidth(CONTROLS_TRAILING_INSET)
        else:
            if width!=self.width():
                self.setFixedWidth(width)
        self.labelFitted.emit(self.width())

    def setText(self,text):
        super().setText(text)
        self.fit_to_label()

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.hover:
            painter.fillRect(self.rect(),QColor(255,255,255,round(18*self.hover)))
        color=QColor(ColorThemeManager.instance().colors.text_primary)
        painter.setPen(color)
        self.icon().paint(painter,12,(self.height()-16)//2,16,16)
        painter.drawText(self.rect().adjusted(34,0,-8,0),Qt.AlignVCenter|Qt.AlignLeft,self.text())


class SectionHeading(QWidget):
    def __init__(self,back,parent=None):
        super().__init__(parent)
        self.back=back

    def paintEvent(self,event):
        colors=ColorThemeManager.instance().colors
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds=self.rect().adjusted(0,0,-1,-1)
        shape=QPainterPath()
        shape.addRoundedRect(bounds,18,18)
        painter.fillPath(shape,QColor(colors.bg_secondary))
        painter.setPen(QPen(QColor(colors.divider),1))
        painter.drawPath(shape)
        x=self.back.geometry().right()+4
        painter.drawLine(x,8,x,self.height()-9)


class LiquidNavBar(GlassPanel):
    """Shared page header, painted as one surface with the window.

    It used to be a floating glass card: rounded, translucent, and inset from
    the page edge by the ``iosNavWrap`` margins. The header now fills with the
    same background the pages use and only marks its lower edge with a hairline
    divider, so the title bar reads as part of the window instead of a panel
    sitting on top of it. The glass panel base is kept for the rest of the
    widget tree (``GlassPanel`` supplies the transparent-background setup).
    """

    #: Left margin of the header content (the window's edge inset).
    LEADING_MARGIN = 14

    #: Right margin of the header content (the same edge inset, mirrored).
    TRAILING_MARGIN = 14

    def __init__(self,title='',parent=None,on_back=None):
        super().__init__(parent)
        ColorThemeManager.instance().theme_changed.connect(self.update)
        self._category_buttons=[]
        self._right_btn=None
        self._controls_inset=0
        self._trailing_inset=CONTROLS_TRAILING_INSET
        root=QVBoxLayout(self)
        root.setContentsMargins(self.LEADING_MARGIN,TOP_MARGIN,self.TRAILING_MARGIN,4)
        root.setSpacing(2)
        row=QGridLayout()
        self._row=row
        row.setHorizontalSpacing(12)
        row.setColumnStretch(1,1)
        self.back_btn=BackCapsule(self)
        self._configure_back_capsule()
        if on_back:
            self.back_btn.clicked.connect(on_back)
        self.heading=SectionHeading(self.back_btn,self)
        heading_layout=QHBoxLayout(self.heading)
        heading_layout.setContentsMargins(3,2,14,2)
        heading_layout.setSpacing(8)
        heading_layout.addWidget(self.back_btn)
        self.icon_lbl=QLabel()
        self.title_lbl=QLabel(title)
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet('font-size:27px;font-weight:650;background:transparent;')
        self.icon_lbl.setFixedSize(30,30)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        title_group=QWidget(self)
        title_layout=QHBoxLayout(title_group)
        title_layout.setContentsMargins(0,0,0,0)
        title_layout.setSpacing(7)
        title_layout.addWidget(self.icon_lbl,0,Qt.AlignVCenter)
        title_layout.addWidget(self.title_lbl,0,Qt.AlignVCenter)
        title_group.setAttribute(Qt.WA_TransparentForMouseEvents)
        heading_layout.addWidget(title_group)
        row.addWidget(self.heading,0,0,1,2,Qt.AlignLeft | Qt.AlignVCenter)
        self._right_layout=QHBoxLayout()
        self._right_layout.addStretch(1)
        row.addLayout(self._right_layout,0,2)
        root.addLayout(row)
        self._categories=QScrollArea()
        self._categories.setWidgetResizable(True)
        self._categories.setFrameShape(QScrollArea.NoFrame)
        self._categories.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._categories.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._categories.setFixedHeight(32)
        self._categories.setStyleSheet('background:transparent;border:none;')
        self._category_content=QWidget()
        self._category_layout=QHBoxLayout(self._category_content)
        self._category_layout.setContentsMargins(0,0,0,0)
        self._category_layout.setSpacing(4)
        self._categories.setWidget(self._category_content)
        self._categories.viewport().installEventFilter(self)
        self._category_content.installEventFilter(self)
        # The pill's fitting fired before the right layout existed; apply the
        # final margins now that every part of the row is in place.
        root.addWidget(self._categories)
        self._apply_leading_margins()
        self._scroll_animation=QVariantAnimation(self)
        self._scroll_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._scroll_animation.valueChanged.connect(lambda value:self._categories.horizontalScrollBar().setValue(round(value)))
        self.setFixedHeight(_HEIGHT)

    def _configure_back_capsule(self):
        """Geometry + content of the back capsule under the window buttons."""
        button=self.back_btn
        colors=ColorThemeManager.instance().colors
        button.setIcon(QIcon(theme_pixmap(':/icon/chevron.left.svg',
                                          colors.text_primary,12,
                                          self.devicePixelRatioF())))
        label=QCoreApplication.translate('Nugget','Back')
        button.setAccessibleName(label)
        button.setToolTip('')
        button.labelFitted.connect(self._apply_leading_margins)
        button.setText(label)   # also fits the button width

    def set_leading_inset(self,px):
        """Reserve room on the left for the window's own buttons.

        The back capsule floats *below* the app-drawn traffic lights and
        claims its own room on the left edge; the title row (which shares its
        vertical band with the buttons) still starts after them (see
        ``src/gui/window_chrome.py``).
        """
        root=self.layout()
        if root is None:
            return
        self._controls_inset=max(0,int(px))
        self._apply_leading_margins()

    def set_trailing_inset(self,px):
        """Reserve room on the right for the window's own buttons.

        The flat chrome (Windows/Linux caption style) ends the button group in
        the top-right corner, where the header's right-side actions used to
        sit; they shift left by the same room a native title bar would keep.
        """
        self._trailing_inset=max(0,int(px))
        self._apply_leading_margins()

    def _apply_leading_margins(self,*_fitted):
        """Keep the title row clear of the window buttons AND the capsule."""
        root=self.layout()
        if root is None:
            return
        # Keep the back button and title together below the window controls.
        root.setContentsMargins(self.LEADING_MARGIN,TOP_MARGIN,self.LEADING_MARGIN,4)
        self._row.setContentsMargins(0,0,0,0)
        # The row can refit its capsule before the right layout exists.
        right=getattr(self,'_right_layout',None)
        if right is not None:
            right.setContentsMargins(0,0,self._trailing_inset,0)
            self._row.setColumnMinimumWidth(2,right.sizeHint().width()+self._trailing_inset)

    def set_back_visible(self,visible):
        self.back_btn.setVisible(visible)
        self._apply_leading_margins()

    def paintEvent(self,event):
        # One surface with the window: same background as the pages, no glass,
        # no rounded box. A single hairline marks where the header ends.
        p=QPainter(self)
        c=ColorThemeManager.instance().colors
        p.fillRect(self.rect(),QColor(c.bg_primary))
        p.setPen(QPen(QColor(c.divider),1))
        y=self.height()-1
        p.drawLine(0,y,self.width(),y)

    def _retheme(self):
        # Colours are read live in paintEvent; a repaint is all that is needed.
        self.update()

    def set_title(self,title):
        self.title_lbl.setText(title)

    def set_icon(self,path):
        self.icon_lbl.setVisible(bool(path))
        if path:
            self.icon_lbl.setPixmap(theme_pixmap(
                path, ColorThemeManager.instance().colors.text_primary,
                30, self.devicePixelRatioF()))

    def set_categories(self,categories):
        while self._category_layout.count():
            item=self._category_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._category_buttons=[]
        self._categories.setVisible(len(categories)>1)
        for title,callback in categories if len(categories)>1 else []:
            button=LiquidButton(title.replace('&','&&'))
            button.setMinimumHeight(32)
            button.setFixedHeight(32)
            button.setFixedWidth(button.sizeHint().width()+10)
            button.clicked.connect(lambda _,b=button,cb=callback:self._jump(b,cb))
            button.installEventFilter(self)
            self._category_layout.addWidget(button)
            self._category_buttons.append(button)
        self._category_layout.addStretch()
        self.setFixedHeight(_HEIGHT_PILLS if len(categories)>1 else _HEIGHT)

    def _jump(self,selected,callback):
        self._selection_started=time.monotonic()
        for button in self._category_buttons:
            button.setProperty('selected',button is selected)
            button.update()
        callback()

    def eventFilter(self,target,event):
        if event.type()==QEvent.Wheel:
            bar=self._categories.horizontalScrollBar()
            delta=event.pixelDelta().x() or event.pixelDelta().y()
            if not delta:
                delta=(event.angleDelta().x()or event.angleDelta().y())/120*90
            if bar.maximum()>0 and delta:
                end=max(0,min(bar.maximum(),bar.value()-round(delta)))
                self._scroll_animation.stop()
                self._scroll_animation.setDuration(0 if QApplication.instance().property('liquid_reduce_motion')else 180)
                self._scroll_animation.setStartValue(bar.value())
                self._scroll_animation.setEndValue(end)
                self._scroll_animation.start()
                return True
        return super().eventFilter(target,event)

    def set_right_action(self,text,callback):
        self.clear_right_action()
        self._right_btn=LiquidButton(text)
        self._right_btn.clicked.connect(callback)
        self._right_layout.addWidget(self._right_btn)

    def clear_right_action(self):
        if self._right_btn:
            self._right_layout.removeWidget(self._right_btn)
            self._right_btn.hide()
            self._right_btn.deleteLater()
            self._right_btn=None
