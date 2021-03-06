//
//  SDConfigProblemReporter.h
//  Zephyros
//
//  Created by Steven on 4/13/13.
//  Copyright (c) 2013 Giant Robot Software. All rights reserved.
//

#import <Cocoa/Cocoa.h>

#define SDLogMessageTypeError @"SDLogMessageTypeError"
#define SDLogMessageTypeUser @"SDLogMessageTypeUser"
#define SDLogMessageTypeRequest @"SDLogMessageTypeRequest"
#define SDLogMessageTypeResponse @"SDLogMessageTypeResponse"

@interface SDLogWindowController : NSWindowController <NSWindowDelegate>

+ (SDLogWindowController*) sharedLogWindowController;

- (void) show:(NSString*)message type:(NSString*)type;
- (void) log:(NSString*)message type:(NSString*)type;

@end
