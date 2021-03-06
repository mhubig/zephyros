//
//  SDTopLevelClientProxy.m
//  Zephyros
//
//  Created by Steven Degutis on 8/12/13.
//  Copyright (c) 2013 Giant Robot Software. All rights reserved.
//

#import "SDTopLevelClientProxy.h"

#import "SDHotKey.h"
#import "SDEventListener.h"
#import "SDMouseFollower.h"

#import "SDFuzzyMatcher.h"
#import "SDConfigLauncher.h"
#import "SDAlertWindowController.h"
#import "SDLogWindowController.h"
#import "SDBoxWindowController.h"

#import "SDWindowProxy.h"

@interface SDTopLevelClientProxy ()

@property NSMutableArray* hotkeys;
@property NSMutableArray* listeners;

@end

@implementation SDTopLevelClientProxy

- (id) init {
    if (self = [super init]) {
        self.hotkeys = [NSMutableArray array];
        self.listeners = [NSMutableArray array];
    }
    return self;
}

- (void) destroy {
    for (SDHotKey* hotkey in self.hotkeys) {
        [hotkey unbind];
    }
    
    for (SDEventListener* listener in self.listeners) {
        [listener stopListening];
    }
}

- (id) bind:(NSArray*)args msgID:(id)msgID {
    SDTypeCheckArg(NSString, key, 0);
    SDTypeCheckArg(NSArray, mods, 1);
    SDTypeCheckArray(mods, NSString);
    
    SDHotKey* hotkey = [[SDHotKey alloc] init];
    hotkey.key = [key uppercaseString];
    hotkey.modifiers = [mods valueForKeyPath:@"uppercaseString"];
    hotkey.fn = ^{
        [self.client sendResponse:nil forID:msgID];
    };
    
    if ([hotkey bind]) {
        [self.hotkeys addObject:hotkey];
    }
    else {
        [self.client showAPIError:[@"Can't bind: " stringByAppendingString: [hotkey hotKeyDescription]]];
    }
    
    return @-1;
}

- (id) unbind:(NSArray*)args msgID:(id)msgID {
    SDTypeCheckArg(NSString, key, 0);
    SDTypeCheckArg(NSArray, mods, 1);
    SDTypeCheckArray(mods, NSString);
    
    key = [key uppercaseString];
    NSArray* modifiers = [mods valueForKeyPath:@"uppercaseString"];
    
    SDHotKey* foundHotkey;
    for (SDHotKey* existingHotkey in self.hotkeys) {
        if ([existingHotkey.key isEqual: key] && [existingHotkey.modifiers isEqual: modifiers]) {
            foundHotkey = existingHotkey;
            break;
        }
    }
    
    if (foundHotkey) {
        [foundHotkey unbind];
        [self.hotkeys removeObject:foundHotkey];
        return @YES;
    }
    else {
        return @NO;
    }
}

- (id) listen:(NSArray*)args msgID:(id)msgID {
    SDTypeCheckArg(NSString, event, 0);
    
    if ([[event uppercaseString] isEqualToString:@"MOUSE_MOVED"]) {
        // only incur the cost for those who wish to pay the price
        [[SDMouseFollower sharedFollower] startListening];
    }
    
    SDEventListener* listener = [[SDEventListener alloc] init];
    listener.eventName = event;
    listener.fn = ^(id thing) {
        [self.client sendResponse:thing forID:msgID];
    };
    
    [listener startListening];
    [self.listeners addObject:listener];
    
    return @-1;
}

- (id) relaunch_config:(NSArray*)args msgID:(id)msgID {
    [[SDConfigLauncher sharedConfigLauncher] launchConfigMaybe];
    return nil;
}

- (id) update_settings:(NSArray*)args msgID:(id)msgID {
    SDTypeCheckArg(NSDictionary, settings, 0);
    
    NSNumber* shouldAnimate = [settings objectForKey:@"alert_should_animate"];
    if ([shouldAnimate isKindOfClass: [NSNumber self]])
        [SDAlerts sharedAlerts].alertAnimates = [shouldAnimate boolValue];
    
    NSNumber* defaultDuration = [settings objectForKey:@"alert_default_delay"];
    if ([defaultDuration isKindOfClass: [NSNumber self]])
        [SDAlerts sharedAlerts].alertDisappearDelay = [defaultDuration doubleValue];
    
    return nil;
}

- (id) clipboard_contents:(NSArray*)args msgID:(id)msgID {
    return [[NSPasteboard generalPasteboard] stringForType:NSPasteboardTypeString];
}

- (id) focused_window:(NSArray*)args msgID:(id)msgID {
    return [SDWindowProxy focusedWindow];
}

- (id) visible_windows:(NSArray*)args msgID:(id)msgID {
    return [SDWindowProxy visibleWindows];
}

- (id) all_windows:(NSArray*)args msgID:(id)msgID {
    return [SDWindowProxy allWindows];
}

- (id) main_screen:(NSArray*)args msgID:(id)msgID {
    return [SDScreenProxy mainScreen];
}

- (id) all_screens:(NSArray*)args msgID:(id)msgID {
    return [SDScreenProxy allScreens];
}

- (id) running_apps:(NSArray*)args msgID:(id)msgID {
    return [SDAppProxy runningApps];
}

- (id) log:(NSArray*)args msgID:(id)msgID {
    SDTypeCheckArg(NSString, str, 0);
    
    [[SDLogWindowController sharedLogWindowController] show:str
                                                       type:SDLogMessageTypeUser];
    return nil;
}

- (id) alert:(NSArray*)args msgID:(id)msgID {
    SDTypeCheckArg(NSString, msg, 0);
    NSNumber* duration = [args objectAtIndex:1];
    
    if ([duration isEqual: [NSNull null]]) {
        [[SDAlerts sharedAlerts] show:msg];
    }
    else {
        [[SDAlerts sharedAlerts] show:msg
                             duration:[duration doubleValue]];
    }
    
    return nil;
}

- (id) show_box:(NSArray*)args msgID:(id)msgID {
    SDTypeCheckArg(NSString, text, 0);
    [[SDBoxWindowController sharedBox] showWithText:text];
    return nil;
}

- (id) hide_box:(NSArray*)args msgID:(id)msgID {
    [[SDBoxWindowController sharedBox] hide];
    return nil;
}

- (id) choose_from:(NSArray*)args msgID:(id)msgID {
    SDTypeCheckArg(NSString, title, 1);
    SDTypeCheckArg(NSNumber, lines, 2);
    SDTypeCheckArg(NSNumber, chars, 3);
    
    SDTypeCheckArg(NSArray, list, 0);
    SDTypeCheckArray(list, NSString);
    
    [NSApp activateIgnoringOtherApps:YES];
    [SDFuzzyMatcher showChoices:list
                      charsWide:[chars intValue]
                      linesTall:[lines intValue]
                    windowTitle:title
                  choseCallback:^(long chosenIndex) {
                      [NSApp hide:self];
                      [self.client sendResponse:@(chosenIndex) forID:msgID];
                  }
               canceledCallback:^{
                   [NSApp hide:self];
                   [self.client sendResponse:[NSNull null] forID:msgID];
               }];
    return @1;
}

@end
